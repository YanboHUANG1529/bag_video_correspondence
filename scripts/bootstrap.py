"""Audit assets, extract native RGB, export example clouds and pending annotations.

This prepares observations. It does not estimate video-to-asset correspondence.
"""
import argparse
import csv
import json
from pathlib import Path
import platform
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import PROJECT, load_obj, read_json, sha256, write_json

RAW = PROJECT / "data/raw/case00"
ACTIVE = RAW / "active"
DERIVED = PROJECT / "data/derived/case00"
OUTPUT = PROJECT / "outputs/bootstrap"


def inspect_asset(name):
    obj = PROJECT / f"data/raw/assets/{name}/bag_{name[-1]}.obj"
    vertices, faces = load_obj(obj)
    # Topological audit uses raw material indices. Coincident vertices are not welded.
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[counts == 1]
    graph = {}
    for a, b in boundary.tolist():
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    components, seen = [], set()
    for start in sorted(graph):
        if start in seen:
            continue
        pending, ids = [start], []
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            ids.append(node)
            pending.extend(graph[node])
        ids = sorted(ids)
        simple = all(len(graph[v]) == 2 for v in ids)
        order = []
        if simple:
            node, previous = ids[0], None
            while node not in order:
                order.append(node)
                next_nodes = [v for v in sorted(graph[node]) if v != previous]
                previous, node = node, next_nodes[0]
        components.append({"candidate_id": len(components), "vertex_ids": ids,
                           "is_simple_cycle": simple, "ordered_vertex_ids": order,
                           "semantic_label": None, "review_status": "pending",
                           "bbox_min_m": vertices[ids].min(0).tolist(),
                           "bbox_max_m": vertices[ids].max(0).tolist()})
    area2 = np.linalg.norm(np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]],
                                   vertices[faces[:, 2]] - vertices[faces[:, 0]]), axis=1)
    out = PROJECT / f"data/derived/assets/{name}"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "topology.npz", vertices=vertices, faces=faces,
                        material_edges=unique, boundary_edges=boundary,
                        source_vertex_ids=np.arange(len(vertices)), source_face_ids=np.arange(len(faces)))
    report = {"asset_id": name, "source_mesh_sha256": sha256(obj), "mesh_index_policy": "raw_obj_order_no_welding",
              "vertex_count": len(vertices), "face_count": len(faces),
              "coincident_vertex_count": len(vertices) - len(np.unique(vertices, axis=0)),
              "degenerate_face_ids": np.flatnonzero(area2 < 1e-12).tolist(),
              "nonmanifold_edge_count": int((counts > 2).sum()),
              "boundary_branch_vertex_ids": [int(v) for v in sorted(graph) if len(graph[v]) != 2],
              "duplicate_face_count": len(faces) - len(np.unique(np.sort(faces, axis=1), axis=0)),
              "boundary_component_count": len(components), "boundary_edge_count": len(boundary),
              "bounds_m": [vertices.min(0).tolist(), vertices.max(0).tolist()],
              "boundary_candidates": components, "semantics_reviewed": False}
    write_json(out / "mesh_audit.json", report)
    template = PROJECT / f"data/annotations/assets/{name}_regions.json"
    if not template.exists():
        write_json(template, {"schema_version": 1, "asset_id": name, "source_mesh_sha256": sha256(obj),
                              "review_status": "pending", "face_index_domain": "raw_obj_zero_based",
                              "parts": [], "material_landmarks": [], "chart_definitions": [],
                              "boundary_candidates_file": f"data/derived/assets/{name}/mesh_audit.json"})
    return {k: report[k] for k in ["asset_id", "vertex_count", "face_count", "boundary_component_count",
                                 "nonmanifold_edge_count", "degenerate_face_ids", "coincident_vertex_count"]}


def extract_native_rgb(rows):
    destination = DERIVED / "rgb_native"
    destination.mkdir(parents=True, exist_ok=True)
    video = cv2.VideoCapture(str(RAW / "input_bundle/input.mp4"))
    if not video.isOpened():
        raise RuntimeError("Cannot decode the original video")
    wanted = {int(row["source_index"]): int(row["active_index"]) for row in rows}
    stats = []
    try:
        for source in range(max(wanted) + 1):
            ok, bgr = video.read()
            if not ok:
                raise RuntimeError("Original video ended before source frame " + str(source))
            if source not in wanted:
                continue
            active = wanted[source]
            path = destination / f"{active:03d}.jpg"
            if not cv2.imwrite(str(path), bgr, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError("Native RGB export failed")
            small = cv2.imread(str(ACTIVE / f"rgb_frames/{active:03d}.jpg"))
            resized = cv2.resize(bgr, (small.shape[1], small.shape[0]))
            stats.append({"active_index": active, "source_index": source,
                          "resized_rgb_mae_8bit": float(np.abs(resized.astype(float) - small.astype(float)).mean())})
    finally:
        video.release()
    if len(stats) != len(rows):
        raise ValueError("Native RGB extraction did not cover the frame map")
    return stats


def export_cloud(frame, config, calibration, transform):
    depth = np.asarray(Image.open(ACTIVE / f"native_depth_frames/{frame:03d}.png"))
    height, width = depth.shape
    native_rgb = np.asarray(Image.open(DERIVED / f"rgb_native/{frame:03d}.jpg").convert("RGB"))
    if native_rgb.shape[:2] != depth.shape:
        raise ValueError("Native RGB/depth dimensions differ")
    bag = Image.open(ACTIVE / f"masks/beige_rigid_bag/masks/{frame:03d}.png").convert("L")
    # Interior mask reduces mixed edge pixels. Hand overlap is excluded, not filled.
    mask = np.asarray(bag.filter(ImageFilter.MinFilter(3)).resize((width, height), Image.Resampling.NEAREST)) > 0
    missing_masks = []
    for side in ["left", "right"]:
        hand_path = ACTIVE / f"masks/{side}/masks/{frame:03d}.png"
        if not hand_path.exists():
            missing_masks.append(side)
            continue
        hand = Image.open(hand_path).convert("L")
        mask &= np.asarray(hand.resize((width, height), Image.Resampling.NEAREST)) == 0
    scale = float(calibration["depth"]["unit_m"])
    z = depth.astype(np.float64) * scale
    lo, hi = config["depth_valid_range_m"]
    valid = mask & (depth > 0) & (z >= lo) & (z <= hi)
    yy, xx = np.nonzero(valid)
    total = len(xx)
    if total == 0:
        raise ValueError("No valid visible bag depth in frame " + str(frame))
    if total > config["max_cloud_points_per_frame"]:
        keep = np.linspace(0, total - 1, config["max_cloud_points_per_frame"], dtype=int)
        xx, yy = xx[keep], yy[keep]
    k = np.asarray(calibration["color"]["K"], float).copy()
    k[0] *= width / calibration["color"]["width"]
    k[1] *= height / calibration["color"]["height"]
    distortion = np.asarray(calibration["color"]["distortion"]["coefficients_k1_k2_p1_p2_k3_k4_k5_k6"], float)
    pixels = np.column_stack([xx, yy])
    rays = cv2.undistortPoints(pixels.astype(np.float64)[:, None, :], k, distortion)[:, 0, :]
    zz = z[yy, xx]
    camera = np.column_stack([rays[:, 0] * zz, rays[:, 1] * zz, zz])
    world = camera @ transform[:3, :3].T + transform[:3, 3]
    folder = DERIVED / "pointclouds"
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / f"{frame:03d}.npz", points_camera_m=camera.astype(np.float32),
                        points_world_m=world.astype(np.float32), pixel_xy_native=pixels,
                        rgb=native_rgb[yy, xx], K_native=k, depth_unit_m=np.asarray(scale))
    return {"active_index": frame, "valid_interior_bag_depth_pixels": total, "exported_points": len(camera),
            "z_range_m": [float(zz.min()), float(zz.max())], "contact_point_depth_measured": False,
            "missing_hand_masks": missing_masks, "occlusion_filter_complete": not missing_masks,
            "metric_evaluation_eligible": False}


def preview(frames, rows):
    sheet = Image.new("RGB", (3 * 480, ((len(frames) + 2) // 3) * 300), "#17212b")
    for index, frame in enumerate(frames):
        image = Image.open(DERIVED / f"rgb_native/{frame:03d}.jpg").convert("RGB")
        size = image.size
        mask = Image.open(ACTIVE / f"masks/beige_rigid_bag/masks/{frame:03d}.png").convert("L")
        mask = mask.resize(size, Image.Resampling.NEAREST)
        tint = Image.new("RGB", size, "#14b8a6")
        image = Image.composite(Image.blend(image, tint, 0.22), image, mask)
        image.thumbnail((480, 270))
        x, y = index % 3 * 480, index // 3 * 300
        sheet.paste(image, (x, y + 25))
        ImageDraw.Draw(sheet).text((x + 8, y + 5), f"active={frame:03d}  source={rows[frame]['source_index']}  mask overlay", fill="white")
    sheet.save(OUTPUT / "contact_sheet.jpg", quality=90)


def annotation_templates(frames, mesh_hash):
    folder = PROJECT / "data/annotations/case00"
    names = ["visible_wall_rim_side_a", "visible_wall_rim_side_b", "visible_wall_rim_middle",
             "visible_handle_attachment_a", "visible_handle_attachment_b", "visible_handle_bridge",
             "visible_wall_seam_a", "visible_wall_seam_b"]
    path = folder / "landmarks.json"
    if not path.exists():
        write_json(path, {"schema_version": 1, "case_id": "case00", "asset_id": "bag2",
                          "source_mesh_sha256": mesh_hash, "review_status": "pending",
                          "pixel_domain": "native_1280x720", "frame_domain": "active",
                          "landmarks": [{"id": name, "part_id": None, "asset_anchor": None,
                                         "observations": [{"active_index": f, "pixel_xy": None,
                                                           "visibility": "unreviewed", "reviewed": False} for f in frames]}
                                        for name in names]})
    path = folder / "contacts.json"
    if not path.exists():
        hint = read_json(RAW / "historical_review/grasp_region.json")
        write_json(path, {"schema_version": 1, "case_id": "case00", "review_status": "pending",
                          "pixel_domain": "native_1280x720", "frame_domain": "active",
                          "contacts": [{"active_index": 30, "hand": "left", "asset_anchor": None,
                                        "part_id": None, "ground_truth": False, "reviewed": False,
                                        "historical_hint": {"pixel_xy": hint["contact_pixel_xy"],
                                                            "opening_fraction": hint["opening_fraction"],
                                                            "direct_contact_depth_available": hint["direct_contact_depth_available"],
                                                            "source": "data/raw/case00/historical_review/grasp_region.json"}},
                                       {"active_index": 90, "hand": "right", "asset_anchor": None,
                                        "part_id": None, "ground_truth": False, "reviewed": False}]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-native-extract", action="store_true", help="Reuse already exported native RGB")
    args = parser.parse_args()
    manifest_path = PROJECT / "data/manifests/local_data_manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("Run prepare_data.py and wait for its successful completion first")
    manifest = read_json(manifest_path)
    missing = [r["destination"] for r in manifest["files"] if not (PROJECT / r["destination"]).is_file()]
    if missing:
        raise FileNotFoundError("Incomplete local dataset: " + str(missing[:3]))
    config = read_json(PROJECT / "configs/exploration.json")
    rows = read_json(ACTIVE / "frame_map.json")["frames"]
    if [r["active_index"] for r in rows] != list(range(len(rows))):
        raise ValueError("Expected sequential active indices")
    sources = [int(r["source_index"]) for r in rows]
    if any(a >= b for a, b in zip(sources, sources[1:])):
        raise ValueError("Source frame indices must be strictly increasing")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)
    stats = None if args.skip_native_extract else extract_native_rgb(rows)
    table = DERIVED / "frame_table.csv"
    start = rows[0]["color_ts_us"]
    with table.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["active_index", "source_index", "pretrim_deximit_index", "time_active_s", "color_ts_us", "depth_ts_us"])
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row[k] for k in writer.fieldnames if k != "time_active_s"},
                             "time_active_s": (row["color_ts_us"] - start) * 1e-6})
    assets = [inspect_asset(name) for name in ["bag1", "bag2", "bag3"]]
    calibration = read_json(ACTIVE / "calibration.json")
    if not calibration.get("depth_registered_to_color"):
        raise ValueError("Depth must be registered to color before this bootstrap")
    transform = np.load(ACTIVE / "T_camera_world.npy", allow_pickle=False)
    if transform.shape != (4, 4) or not np.isfinite(transform).all() or not np.allclose(transform[3], [0, 0, 0, 1]):
        raise ValueError("Invalid camera-to-world transform")
    frames = config["bootstrap_frames_active"]
    clouds = [export_cloud(frame, config, calibration, transform) for frame in frames]
    preview(frames, rows)
    annotation_templates(frames, sha256(PROJECT / "data/raw/assets/bag2/bag_2.obj"))
    report = {"schema_version": 1, "status": "observations_prepared", "frame_count": len(rows),
              "assets": assets, "example_clouds": clouds, "native_rgb_alignment": stats,
              "projection": "registered_color_grid_with_opencv_rational_undistortPoints",
              "projection_assumption": "registered depth values are optical-axis z in the color-camera frame; validate physically before metric evaluation",
              "world_transform_source": "upstream table-based estimate; not robot hand-eye calibration",
              "annotations_reviewed": False, "correspondence_estimated": False,
              "environment": {"python": platform.python_version(), "numpy": np.__version__,
                              "opencv": cv2.__version__, "pillow": Image.__version__, "platform": sys.platform}}
    write_json(OUTPUT / "bootstrap_report.json", report)
    print(json.dumps({"frames": len(rows), "native_rgb_frames": len(list((DERIVED / "rgb_native").glob("*.jpg"))),
                      "example_clouds": len(clouds), "assets": assets, "correspondence_estimated": False}))


if __name__ == "__main__":
    main()
