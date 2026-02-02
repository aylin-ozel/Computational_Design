import Rhino.Geometry as rg
import random
import math


class OrganicGrowthSystem:
    def __init__(self, start_curve, params):
        self.current_curve = start_curve.Duplicate()
        self.iterations = int(params.get('iterations', 10))
        self.z_dist = params.get('z_dist', 1.0)
        self.prob = params.get('prob', 0.5)
        self.shrink = params.get('shrink', 0.8)
        self.size_proportion = params.get('size_proportion', 1.5)

        # BRANCH RANDOMIZATION
        self.min_L1 = params.get('min_L1', 2.0)
        self.max_L1 = params.get('max_L1', 5.0)
        self.min_L3 = params.get('min_L3', 1.5)
        self.max_L3 = params.get('max_L3', 4.0)
        self.jitter = params.get('jitter', 0.3)

        # BRANCH SCALE
        self.branch_scale_min = params.get('branch_scale_min', 0.6)
        self.branch_scale_max = params.get('branch_scale_max', 1.4)
        self.branch_segment_min = params.get('branch_segment_min', 2)
        self.branch_segment_max = params.get('branch_segment_max', 5)

        # STEPPED STRUCTURE
        self.base_offset = params.get('xy_off', 1.0)
        self.taper_factor = params.get('taper_factor', 0.95)
        self.decay_rate = params.get('decay_rate', 0.02)

        # MINIMUM SIZE
        self.initial_length = self.current_curve.GetLength()
        self.min_length = self.initial_length * 0.35

        self.current_trim = params.get('step_base', 0.1)
        self.history = []
        random.seed(params.get('seed', 1))

    def _get_random_length(self, min_val, max_val, iter_idx):
        """Tamamen rastgele uzunluk"""
        decay = self.taper_factor ** iter_idx
        base_range = random.uniform(min_val, max_val) * decay
        jitter_amount = base_range * self.jitter
        return base_range + random.uniform(-jitter_amount, jitter_amount)

    def _grow_flat_random_branch(self, start_pt, start_dir, anterior_len, is_clockwise, iter_idx):
        """
        DÜZ katmanda branch - Z değişmez, sadece XY düzleminde
        Her branch farklı boyut ve segment sayısı
        """
        lines = []
        curr_pos = start_pt
        curr_dir = rg.Vector3d(start_dir)
        if not curr_dir.Unitize():
            return lines

        # Rastgele segment sayısı
        num_segments = random.randint(
            self.branch_segment_min, self.branch_segment_max)

        # İlk segment - büyük ve rastgele
        initial_segment_length = self._get_random_length(
            self.min_L1, self.max_L1, iter_idx)

        # Scale factor - içe veya dışa
        segment_scale = random.uniform(
            self.branch_scale_min, self.branch_scale_max)

        # Dönüş açısı
        angle = -math.pi / 2 if is_clockwise else math.pi / 2

        current_length = initial_segment_length

        for i in range(num_segments):
            # 90 derece dön
            curr_dir.Rotate(angle, rg.Vector3d.ZAxis)

            # Segment uzunluğu
            if i == 0:
                seg_len = current_length
            else:
                seg_len = current_length * random.uniform(0.7, 1.1)

            # Yeni nokta - Z SABİT KALIYOR (düz katman)
            new_p = rg.Point3d(
                curr_pos.X + curr_dir.X * seg_len,
                curr_pos.Y + curr_dir.Y * seg_len,
                curr_pos.Z  # ← Z DEĞİŞMİYOR!
            )

            lines.append(rg.LineCurve(curr_pos, new_p))
            curr_pos = new_p

            # Bir sonraki segment için
            current_length *= segment_scale

        return lines

    def run(self):
        for i in range(self.iterations):
            self.current_curve.Domain = rg.Interval(0, 1)
            total_len = self.current_curve.GetLength()

            # 1. GRADUAL TRIM
            potential_trim = self.current_trim + (total_len * self.decay_rate)
            resulting_len = total_len - (2 * potential_trim)

            if resulting_len > self.min_length:
                self.current_trim = potential_trim
            else:
                self.current_trim = (total_len - self.min_length) / 2

            self.current_trim = max(0, self.current_trim)

            t_start = self.current_trim / total_len
            t_end = 1.0 - (self.current_trim / total_len)

            shrunk_curve = self.current_curve.Trim(t_start, t_end)
            if not shrunk_curve:
                break

            # 2. FLAT RANDOM BRANCHING
            to_join = [shrunk_curve]
            success, polyline = shrunk_curve.TryGetPolyline()

            if success and polyline.Count >= 2:
                p0, p_last = polyline[0], polyline[polyline.Count - 1]

                # Branch uzunlukları tamamen random
                branch_len_start = random.uniform(
                    self.min_L1 * 0.8, self.max_L1 * 1.2)
                branch_len_end = random.uniform(
                    self.min_L1 * 0.8, self.max_L1 * 1.2)

                # Daha fazla branch
                branch_prob = min(self.prob * 1.3, 0.9)

                if random.random() < branch_prob:
                    branches = self._grow_flat_random_branch(
                        p0,
                        p0 - polyline[1],
                        branch_len_start,
                        True,
                        i
                    )
                    for seg in branches:
                        seg.Reverse()
                    branches.reverse()
                    to_join = branches + to_join

                if random.random() < branch_prob:
                    branches = self._grow_flat_random_branch(
                        p_last,
                        p_last - polyline[polyline.Count-2],
                        branch_len_end,
                        False,
                        i
                    )
                    to_join.extend(branches)

            # 3. JOIN AND OFFSET
            joined = rg.Curve.JoinCurves(to_join, 0.01)
            if not joined:
                break

            temp_curve = joined[0]
            current_offset = self.base_offset * \
                (self.taper_factor ** i) * random.uniform(0.8, 1.2)

            offset_result = temp_curve.Offset(
                rg.Plane.WorldXY,
                current_offset,
                0.01,
                rg.CurveOffsetCornerStyle.Sharp
            )

            if offset_result:
                self.current_curve = offset_result[0]
            else:
                self.current_curve = temp_curve

            # 4. Z-MOVE SADECE BURADA - TÜM KATMAN BİRDEN YÜKSELİR
            self.current_curve.Transform(
                rg.Transform.Translation(0, 0, self.z_dist))
            self.history.append(self.current_curve.DuplicateCurve())

        return self.history


# =========================================================
# GH SCRIPT AREA
# =========================================================
params = {
    'iterations': N,
    'step_base': Step,
    'xy_off': XY_Off,
    'z_dist': Z_Dist,
    'seed': Seed,
    'prob': prob,
    'shrink': shrink,
    'size_proportion': size_proportion,
    'decay_rate': 0.01,
    'taper_factor': 0.98,

    # RANDOM BRANCH PARAMETRELERİ
    'min_L1': 2.5,       # Büyük başlangıç
    'max_L1': 6.0,       # Çok büyük branch'lar
    'min_L3': 1.5,
    'max_L3': 4.0,
    'jitter': 0.35,      # Fazla varyasyon

    # BRANCH SCALE
    'branch_scale_min': 0.65,   # Hızlı küçülme
    'branch_scale_max': 0.95,   # Yavaş küçülme

    # SEGMENT SAYISI
    'branch_segment_min': 3,
    'branch_segment_max': 6,
}

system = OrganicGrowthSystem(C, params)
a = system.run()
