import Rhino.Geometry as rg
import random

__gh_api_version__ = 1

def run(
    base_w=18.0,
    base_h=12.0,
    iterations=14,
    offset_dist=1.0,
    step_height=0.6,
    prob_selection=0.2,
    prop_depth=0.3,
    prop_width=0.3,
    branch_limit=3,
    # branch mini-ziggurat
    branch_steps=5,
    branch_offset=-0.5,
    branch_step_height=0.6,
    # reproducibility
    seed=None
):
    """
    Returns:
        terraces: list[rg.Curve] (PolylineCurves)
    """

    if seed is not None:
        random.seed(int(seed))

    # ----------------------------
    # INITIALIZATION
    # ----------------------------
    pts_list = [
        rg.Point3d(0, base_h, 0),
        rg.Point3d(0, 0, 0),
        rg.Point3d(base_w, 0, 0),
        rg.Point3d(base_w, base_h, 0)
    ]

    terraces = []
    branch_count = 0

    # ----------------------------
    # BRANCH MINI-ZIGGURAT (inner helper)
    # ----------------------------
    def branch_ziggurat(start_pts):
        nonlocal terraces

        local_pl = rg.Polyline(start_pts)
        current_curve = local_pl.ToPolylineCurve()

        for i in range(int(branch_steps)):
            dz = 0.0 if i == 0 else -float(branch_step_height)

            moved = current_curve.Duplicate()
            moved.Transform(rg.Transform.Translation(0, 0, dz))
            terraces.append(moved)

            offset_res = moved.Offset(
                rg.Plane.WorldXY,
                float(branch_offset),
                0.01,
                rg.CurveOffsetCornerStyle.Sharp
            )

            if not offset_res:
                break

            current_curve = offset_res[0]

    # ----------------------------
    # MAIN LOOP
    # ----------------------------
    for _ in range(int(iterations)):
        current_pl = rg.Polyline(pts_list)
        terraces.append(current_pl.ToPolylineCurve())

        offset_res = current_pl.ToPolylineCurve().Offset(
            rg.Plane.WorldXY,
            float(offset_dist),
            0.01,
            rg.CurveOffsetCornerStyle.Sharp
        )

        if not offset_res:
            break

        success, nc_pl = offset_res[0].TryGetPolyline()
        if not success:
            break

        next_pts = list(nc_pl)

        if branch_count < int(branch_limit) and random.random() < float(prob_selection):
            # LEFT
            tip_l, elbow_l = next_pts[0], next_pts[1]
            tan_l = tip_l - elbow_l
            L_l = tan_l.Length
            if L_l > 1e-9:
                tan_l.Unitize()
                perp_l = rg.Vector3d.CrossProduct(tan_l, rg.Vector3d.ZAxis)

                p1_l = tip_l + perp_l * (L_l * float(prop_depth))
                p2_l = p1_l - tan_l * (L_l * float(prop_width))
                p3_l = p2_l - perp_l * (L_l * float(prop_depth))

                next_pts.insert(0, p1_l)
                next_pts.insert(0, p2_l)
                next_pts.insert(0, p3_l)

                branch_ziggurat([p3_l, p2_l, p1_l, tip_l])

            # RIGHT
            tip_r, elbow_r = next_pts[-1], next_pts[-2]
            tan_r = tip_r - elbow_r
            L_r = tan_r.Length
            if L_r > 1e-9:
                tan_r.Unitize()
                perp_r = rg.Vector3d.CrossProduct(tan_r, rg.Vector3d.ZAxis) * -1

                p1_r = tip_r + perp_r * (L_r * float(prop_depth))
                p2_r = p1_r - tan_r * (L_r * float(prop_width))
                p3_r = p2_r - perp_r * (L_r * float(prop_depth))

                next_pts.extend([p1_r, p2_r, p3_r])

                branch_ziggurat([tip_r, p1_r, p2_r, p3_r])

            branch_count += 1

        # lift points each iteration
        for p in next_pts:
            p.Transform(rg.Transform.Translation(0, 0, float(step_height)))

        pts_list = next_pts

    return terraces


# Optional: lets you run a sanity check in Rhino's Python (not GH)
if __name__ == "__main__":
    t = run(seed=1)
    print(f"terraces: {len(t)}")
