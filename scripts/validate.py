"""Validate the prepared data and report remaining annotation prerequisites."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from common import PROJECT, contained, load_obj, read_json, sha256, write_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read_json(PROJECT / "data/manifests/local_data_manifest.json")
    for row in manifest["files"]:
        path = contained(PROJECT, row["destination"])
        require(path.is_file(), "Missing copied file: " + row["destination"])
        require(path.stat().st_size == row["bytes"], "Size changed: " + row["destination"])
        require(sha256(path) == row["sha256"], "SHA-256 changed: " + row["destination"])
    active = PROJECT / "data/raw/case00/active"
    rows = read_json(active / "frame_map.json")["frames"]
    frame_ids = set(range(len(rows)))
    for folder, suffix in [(active / "rgb_frames", ".jpg"), (active / "native_depth_frames", ".png"),
                           (active / "masks/beige_rigid_bag/masks", ".png"),
                           (PROJECT / "data/derived/case00/rgb_native", ".jpg")]:
        require({int(p.stem) for p in folder.glob("*" + suffix)} == frame_ids, "Incomplete frame set: " + str(folder))
    missing_masks = {}
    for side in ["left", "right"]:
        present = {int(p.stem) for p in (active / f"masks/{side}/masks").glob("*.png")}
        missing_masks[side] = sorted(frame_ids - present)
        track = np.load(active / f"data/case_00_native_rgbd/hand_poses/{side}.npy", allow_pickle=False)
        require(track.shape == (len(rows), 4, 4) and np.isfinite(track).all(), "Invalid hand pose track")
    calibration = read_json(active / "calibration.json")
    require(calibration["depth_registered_to_color"] is True, "Unregistered depth")
    unit = calibration["depth"]["unit_m"]
    require(unit == 0.001, "Unexpected depth units; review config and projection")
    k = np.asarray(calibration["color"]["K"], float)
    require(k.shape == (3, 3) and k[0, 0] > 0 and k[1, 1] > 0, "Invalid intrinsics")
    transform = np.load(active / "T_camera_world.npy", allow_pickle=False)
    require(transform.shape == (4, 4) and np.isfinite(transform).all(), "Invalid extrinsic shape")
    require(np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-4), "Nonorthogonal extrinsic rotation")
    clouds = sorted((PROJECT / "data/derived/case00/pointclouds").glob("*.npz"))
    config = read_json(PROJECT / "configs/exploration.json")
    require({int(p.stem) for p in clouds} == set(config["bootstrap_frames_active"]), "Missing example clouds")
    for path in clouds:
        f = int(path.stem)
        with np.load(path, allow_pickle=False) as cloud:
            camera, world, pixels = cloud["points_camera_m"], cloud["points_world_m"], cloud["pixel_xy_native"]
            depth = np.asarray(Image.open(active / f"native_depth_frames/{f:03d}.png"))
            require(depth.dtype == np.uint16 and depth.shape == (720, 1280), "Unexpected native depth format")
            require(len(camera) > 0 and camera.shape == world.shape and camera.shape[1] == 3, "Invalid point cloud shape")
            require(np.isfinite(camera).all() and np.isfinite(world).all(), "Nonfinite cloud")
            values = depth[pixels[:, 1], pixels[:, 0]]
            require((values > 0).all(), "Filled or invalid depth entered the cloud")
            require(np.allclose(camera[:, 2], values * unit, atol=1e-6), "Depth scale/pixel indexing mismatch")
            expected = camera @ transform[:3, :3].T + transform[:3, 3]
            require(np.allclose(world, expected, atol=1e-6), "Camera/world transform mismatch")
            # A round trip detects mismatched distortion and pixel conventions.
            dist = np.asarray(calibration["color"]["distortion"]["coefficients_k1_k2_p1_p2_k3_k4_k5_k6"])
            reprojection, _ = cv2.projectPoints(camera.astype(float), np.zeros(3), np.zeros(3), cloud["K_native"], dist)
            require(np.max(np.linalg.norm(reprojection[:, 0] - pixels, axis=1)) < 0.1, "Pixel reprojection mismatch")
    assets = []
    for name in ["bag1", "bag2", "bag3"]:
        obj = PROJECT / f"data/raw/assets/{name}/bag_{name[-1]}.obj"
        vertices, faces = load_obj(obj)
        audit = read_json(PROJECT / f"data/derived/assets/{name}/mesh_audit.json")
        require(sha256(obj) == audit["source_mesh_sha256"], "Asset mesh fingerprint mismatch")
        with np.load(PROJECT / f"data/derived/assets/{name}/topology.npz", allow_pickle=False) as topology:
            require(np.array_equal(topology["faces"], faces) and np.array_equal(topology["vertices"], vertices), "Raw mesh indices were changed")
        assets.append({"asset_id": name, "vertices": len(vertices), "faces": len(faces),
                       "boundary_branch_vertex_ids": audit["boundary_branch_vertex_ids"]})
    landmarks = read_json(PROJECT / "data/annotations/case00/landmarks.json")
    reviewed = 0
    for landmark in landmarks["landmarks"]:
        for observation in landmark["observations"]:
            require(observation["active_index"] in frame_ids, "Annotation frame is out of range")
            pixel = observation["pixel_xy"]
            if pixel is not None:
                require(len(pixel) == 2 and np.isfinite(pixel).all() and 0 <= pixel[0] < 1280 and 0 <= pixel[1] < 720,
                        "Annotation is outside the native image")
            reviewed += int(observation["reviewed"])
        anchor = landmark["asset_anchor"]
        if anchor is not None:
            require(anchor["source_mesh_sha256"] == landmarks["source_mesh_sha256"], "Stale annotation mesh fingerprint")
            require(0 <= anchor["face_id"] < assets[1]["faces"], "Anchor face out of range")
            bary = np.asarray(anchor["barycentric"], float)
            require(bary.shape == (3,) and np.isfinite(bary).all() and (bary >= 0).all() and abs(bary.sum() - 1) < 1e-6,
                    "Invalid barycentric anchor")
    for path in (PROJECT / "schemas").glob("*.json"):
        read_json(path)
    for name in ["README.md", "docs/PLAN_ZH.md", "docs/TECHNICAL_ROUTE_ZH.md", "docs/DATA_PREPARATION_ZH.md", "docs/ANNOTATION_GUIDE_ZH.md", "docs/REFERENCES_ZH.md", "ccfa.yaml"]:
        content = (PROJECT / name).read_text(encoding="utf-8")
        require("\ufffd" not in content, "Broken UTF-8 text: " + name)
    report = {"schema_version": 1, "integrity_status": "passed", "copied_files_verified": len(manifest["files"]),
              "copied_bytes": manifest["summary"]["total_bytes"], "upstream_verified_files": manifest["summary"]["upstream_verified_count"],
              "active_frames": len(rows), "example_clouds": len(clouds), "assets": assets,
              "missing_hand_masks": missing_masks, "reviewed_landmark_observations": reviewed,
              "ready_for_manual_annotation": True, "registration_implemented": False,
              "human_annotation_gate": "pending", "physical_calibration_gate": "pending",
              "algorithm_evaluation_status": "not_started"}
    write_json(PROJECT / "outputs/bootstrap/validation_report.json", report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
