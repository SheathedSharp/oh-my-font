"""Per-weight design spec for the 0.500 family.

Regular 400 upright is absent on purpose: that cut is the approved 0.400
drawing and is never retargeted. Numbers are hand-set per weight and per
family. They are not a single stem delta, and they do not lie on a straight
line from Thin to Black.
"""
from __future__ import annotations

WEIGHTS = (100, 300, 400, 500, 600, 700, 800, 900)
WEIGHT_NAMES = {
    100: 'Thin', 300: 'Light', 400: 'Regular', 500: 'Medium',
    600: 'Semibold', 700: 'Bold', 800: 'Extrabold', 900: 'Black',
}
# Measured on the approved Regular masters (median straight-stem cuts of H/I).
REFERENCE_STEMS = {
    'LihuiT': {'vertical': 89, 'horizontal': 74},
    'zayJu': {'vertical': 102, 'horizontal': 86},
}

# Sculpt keys applied to the approved skeleton before the stroke model,
# plus hole scales applied after it. 1.0 / 0 means "no extra proportion edit".
# upper_bowl/lower_bowl: horizontal scale of that bowl away from the stem.
# waist: units the right-side waist moves left (positive pinches).
# valley: units the M/W crotch moves up (positive shallower).
# splay: units the outer legs move apart.
# bar: units the e/a bar moves up.
# aperture: units a right-side terminal opens.
# upper_hole/lower_hole: scale of that counter around its own center.

def _row(v, h, join, modulation, tracking, kern, space, counter, oblique, sculpt):
    return {
        'v_stem': v, 'h_stem': h, 'join_stem': join, 'modulation': modulation,
        'tracking': tracking, 'kern_scale': kern, 'space_delta': space,
        'min_counter_ratio': counter, 'oblique': oblique, 'sculpt': sculpt,
    }

# LihuiT stays the quieter text voice: lower contrast, more air, softer traps.
LIHUIT = {
    100: _row(34, 26, 48, 0.62, 34, 0.60, 30, None,
              {'counter_shear_keep': 0.05, 'pad': 20, 'aperture': 5},
              {
                  'B': {'upper_bowl': 1.07, 'lower_bowl': 1.04, 'waist': -6, 'upper_hole': 1.10, 'lower_hole': 1.12},
                  'M': {'valley': 22, 'splay': 12},
                  'R': {'leg': 14, 'crotch': 4, 'upper_hole': 1.08},
                  'a': {'bar': 10, 'aperture': 12, 'hole': 1.10},
                  'g': {'aperture': 8, 'hole': 1.12, 'descender': 10},
                  'e': {'bar': 16, 'aperture': 14, 'hole': 1.08},
                  'two': {'base': 8, 'gap': 10},
                  'three': {'aperture': 12, 'upper_hole': 1.08, 'lower_hole': 1.06},
                  'six': {'aperture': 10, 'hole': 1.10},
                  'eight': {'upper_hole': 1.14, 'lower_hole': 1.08},
                  'nine': {'aperture': 10, 'hole': 1.10},
              }),
    300: _row(58, 48, 66, 0.80, 14, 0.82, 12, None,
              {'counter_shear_keep': 0.05, 'pad': 14, 'aperture': 3},
              {
                  'B': {'upper_bowl': 1.03, 'lower_bowl': 1.02, 'waist': -2, 'upper_hole': 1.04, 'lower_hole': 1.05},
                  'M': {'valley': 8, 'splay': 5},
                  'R': {'leg': 6, 'crotch': 2, 'upper_hole': 1.03},
                  'a': {'bar': 4, 'aperture': 5, 'hole': 1.04},
                  'g': {'aperture': 3, 'hole': 1.05, 'descender': 4},
                  'e': {'bar': 7, 'aperture': 6, 'hole': 1.03},
                  'two': {'base': 3, 'gap': 4},
                  'three': {'aperture': 5, 'upper_hole': 1.03, 'lower_hole': 1.02},
                  'six': {'aperture': 4, 'hole': 1.04},
                  'eight': {'upper_hole': 1.05, 'lower_hole': 1.03},
                  'nine': {'aperture': 4, 'hole': 1.04},
              }),
    500: _row(108, 94, 100, 0.88, -8, 1.08, -6, 0.78,
              {'counter_shear_keep': 0.08, 'pad': 16, 'aperture': 4},
              {
                  'B': {'upper_bowl': 0.98, 'lower_bowl': 1.01, 'waist': 4, 'upper_hole': 0.96, 'lower_hole': 1.02},
                  'M': {'valley': -6, 'splay': -2},
                  'R': {'leg': -2, 'crotch': 3, 'upper_hole': 0.97},
                  'a': {'bar': -2, 'aperture': 3, 'hole': 0.98},
                  'g': {'aperture': 2, 'hole': 0.98, 'descender': -2},
                  'e': {'bar': -3, 'aperture': 4, 'hole': 0.99},
                  'two': {'base': -1, 'gap': 2},
                  'three': {'aperture': 3, 'upper_hole': 0.98, 'lower_hole': 1.00},
                  'six': {'aperture': 3, 'hole': 0.98},
                  'eight': {'upper_hole': 0.97, 'lower_hole': 1.01},
                  'nine': {'aperture': 3, 'hole': 0.98},
              }),
    600: _row(126, 114, 114, 0.74, -14, 1.18, -10, 0.64,
              {'counter_shear_keep': 0.11, 'pad': 18, 'aperture': 6},
              {
                  'B': {'upper_bowl': 0.95, 'lower_bowl': 1.00, 'waist': 8, 'upper_hole': 0.90, 'lower_hole': 0.98},
                  'M': {'valley': -10, 'splay': -4},
                  'R': {'leg': -6, 'crotch': 6, 'upper_hole': 0.92},
                  'a': {'bar': -4, 'aperture': 6, 'hole': 0.94},
                  'g': {'aperture': 5, 'hole': 0.94, 'descender': -4},
                  'e': {'bar': -6, 'aperture': 8, 'hole': 0.96},
                  'two': {'base': -2, 'gap': 5},
                  'three': {'aperture': 6, 'upper_hole': 0.94, 'lower_hole': 0.98},
                  'six': {'aperture': 6, 'hole': 0.94},
                  'eight': {'upper_hole': 0.90, 'lower_hole': 0.98},
                  'nine': {'aperture': 6, 'hole': 0.94},
              }),
    700: _row(150, 138, 132, 0.56, -6, 1.24, -4, 0.52,
              {'counter_shear_keep': 0.15, 'pad': 24, 'aperture': 9},
              {
                  'B': {'upper_bowl': 0.92, 'lower_bowl': 0.99, 'waist': 12, 'upper_hole': 0.84, 'lower_hole': 0.96},
                  'M': {'valley': -4, 'splay': -2},
                  'R': {'leg': -10, 'crotch': 9, 'upper_hole': 0.86},
                  'a': {'bar': -2, 'aperture': 9, 'hole': 0.90},
                  'g': {'aperture': 8, 'hole': 0.90, 'descender': -6},
                  'e': {'bar': -4, 'aperture': 11, 'hole': 0.94},
                  'two': {'base': 2, 'gap': 8},
                  'three': {'aperture': 9, 'upper_hole': 0.88, 'lower_hole': 0.96},
                  'six': {'aperture': 9, 'hole': 0.90},
                  'eight': {'upper_hole': 0.84, 'lower_hole': 0.96},
                  'nine': {'aperture': 9, 'hole': 0.90},
              }),
    800: _row(176, 166, 152, 0.40, 8, 1.16, 6, 0.42,
              {'counter_shear_keep': 0.19, 'pad': 28, 'aperture': 12},
              {
                  'B': {'upper_bowl': 0.88, 'lower_bowl': 0.97, 'waist': 16, 'upper_hole': 0.78, 'lower_hole': 0.92},
                  'M': {'valley': 6, 'splay': 2},
                  'R': {'leg': -12, 'crotch': 12, 'upper_hole': 0.80},
                  'a': {'bar': 0, 'aperture': 12, 'hole': 0.86},
                  'g': {'aperture': 11, 'hole': 0.86, 'descender': -8},
                  'e': {'bar': -2, 'aperture': 14, 'hole': 0.90},
                  'two': {'base': 4, 'gap': 11},
                  'three': {'aperture': 12, 'upper_hole': 0.82, 'lower_hole': 0.92},
                  'six': {'aperture': 12, 'hole': 0.86},
                  'eight': {'upper_hole': 0.76, 'lower_hole': 0.92},
                  'nine': {'aperture': 12, 'hole': 0.86},
              }),
    900: _row(204, 196, 174, 0.28, 22, 1.06, 16, 0.34,
              {'counter_shear_keep': 0.24, 'pad': 34, 'aperture': 16},
              {
                  'B': {'upper_bowl': 0.84, 'lower_bowl': 0.96, 'waist': 20, 'upper_hole': 0.72, 'lower_hole': 0.90},
                  'M': {'valley': 14, 'splay': 6},
                  'R': {'leg': -14, 'crotch': 16, 'upper_hole': 0.74},
                  'a': {'bar': 2, 'aperture': 16, 'hole': 0.82},
                  'g': {'aperture': 14, 'hole': 0.82, 'descender': -6},
                  'e': {'bar': 2, 'aperture': 18, 'hole': 0.88},
                  'two': {'base': 6, 'gap': 14},
                  'three': {'aperture': 16, 'upper_hole': 0.76, 'lower_hole': 0.90},
                  'six': {'aperture': 15, 'hole': 0.82},
                  'eight': {'upper_hole': 0.70, 'lower_hole': 0.88},
                  'nine': {'aperture': 15, 'hole': 0.82},
              }),
}

# zayJu is the display voice: more contrast when light, heavier and more
# sculpted when dark, and it does not track LihuiT's stem table.
ZAYJU = {
    100: _row(28, 16, 42, 0.48, 20, 0.52, 16, None,
              {'counter_shear_keep': 0.07, 'pad': 16, 'aperture': 7},
              {
                  'B': {'upper_bowl': 1.05, 'lower_bowl': 1.06, 'waist': -4, 'upper_hole': 1.08, 'lower_hole': 1.16},
                  'M': {'valley': 10, 'splay': 8},
                  'R': {'leg': 18, 'crotch': 5, 'upper_hole': 1.06},
                  'a': {'bar': 6, 'aperture': 16, 'hole': 1.08},
                  'g': {'aperture': 10, 'hole': 1.14, 'descender': 14},
                  'e': {'bar': 20, 'aperture': 16, 'hole': 1.06},
                  'two': {'base': 12, 'gap': 12},
                  'three': {'aperture': 14, 'upper_hole': 1.06, 'lower_hole': 1.10},
                  'six': {'aperture': 12, 'hole': 1.12},
                  'eight': {'upper_hole': 1.16, 'lower_hole': 1.06},
                  'nine': {'aperture': 12, 'hole': 1.10},
              }),
    300: _row(66, 46, 74, 0.72, 8, 0.78, 6, None,
              {'counter_shear_keep': 0.07, 'pad': 12, 'aperture': 4},
              {
                  'B': {'upper_bowl': 1.02, 'lower_bowl': 1.03, 'waist': 1, 'upper_hole': 1.02, 'lower_hole': 1.08},
                  'M': {'valley': 2, 'splay': 3},
                  'R': {'leg': 8, 'crotch': 2, 'upper_hole': 1.02},
                  'a': {'bar': 3, 'aperture': 7, 'hole': 1.03},
                  'g': {'aperture': 4, 'hole': 1.06, 'descender': 6},
                  'e': {'bar': 10, 'aperture': 7, 'hole': 1.02},
                  'two': {'base': 5, 'gap': 5},
                  'three': {'aperture': 6, 'upper_hole': 1.02, 'lower_hole': 1.04},
                  'six': {'aperture': 5, 'hole': 1.05},
                  'eight': {'upper_hole': 1.06, 'lower_hole': 1.02},
                  'nine': {'aperture': 5, 'hole': 1.04},
              }),
    500: _row(126, 100, 112, 0.86, -12, 1.14, -8, 0.72,
              {'counter_shear_keep': 0.10, 'pad': 16, 'aperture': 6},
              {
                  'B': {'upper_bowl': 0.96, 'lower_bowl': 1.02, 'waist': 8, 'upper_hole': 0.92, 'lower_hole': 1.04},
                  'M': {'valley': -14, 'splay': -4},
                  'R': {'leg': 4, 'crotch': 5, 'upper_hole': 0.94},
                  'a': {'bar': -2, 'aperture': 4, 'hole': 0.96},
                  'g': {'aperture': 3, 'hole': 0.96, 'descender': -2},
                  'e': {'bar': 4, 'aperture': 5, 'hole': 0.97},
                  'two': {'base': 1, 'gap': 3},
                  'three': {'aperture': 4, 'upper_hole': 0.95, 'lower_hole': 1.02},
                  'six': {'aperture': 4, 'hole': 0.96},
                  'eight': {'upper_hole': 0.94, 'lower_hole': 1.03},
                  'nine': {'aperture': 4, 'hole': 0.96},
              }),
    600: _row(152, 126, 130, 0.66, -18, 1.26, -14, 0.58,
              {'counter_shear_keep': 0.14, 'pad': 22, 'aperture': 9},
              {
                  'B': {'upper_bowl': 0.92, 'lower_bowl': 1.00, 'waist': 14, 'upper_hole': 0.84, 'lower_hole': 1.00},
                  'M': {'valley': -18, 'splay': -6},
                  'R': {'leg': -4, 'crotch': 8, 'upper_hole': 0.86},
                  'a': {'bar': -4, 'aperture': 8, 'hole': 0.90},
                  'g': {'aperture': 7, 'hole': 0.90, 'descender': -6},
                  'e': {'bar': -2, 'aperture': 10, 'hole': 0.94},
                  'two': {'base': 0, 'gap': 7},
                  'three': {'aperture': 8, 'upper_hole': 0.88, 'lower_hole': 0.98},
                  'six': {'aperture': 8, 'hole': 0.90},
                  'eight': {'upper_hole': 0.84, 'lower_hole': 0.98},
                  'nine': {'aperture': 8, 'hole': 0.90},
              }),
    700: _row(184, 160, 156, 0.46, -8, 1.30, -6, 0.44,
              {'counter_shear_keep': 0.18, 'pad': 28, 'aperture': 13},
              {
                  'B': {'upper_bowl': 0.86, 'lower_bowl': 0.98, 'waist': 20, 'upper_hole': 0.74, 'lower_hole': 0.94},
                  'M': {'valley': -8, 'splay': 0},
                  'R': {'leg': -8, 'crotch': 12, 'upper_hole': 0.78},
                  'a': {'bar': 0, 'aperture': 12, 'hole': 0.84},
                  'g': {'aperture': 11, 'hole': 0.84, 'descender': -8},
                  'e': {'bar': 2, 'aperture': 14, 'hole': 0.90},
                  'two': {'base': 4, 'gap': 11},
                  'three': {'aperture': 12, 'upper_hole': 0.80, 'lower_hole': 0.94},
                  'six': {'aperture': 12, 'hole': 0.84},
                  'eight': {'upper_hole': 0.74, 'lower_hole': 0.94},
                  'nine': {'aperture': 12, 'hole': 0.84},
              }),
    800: _row(214, 194, 176, 0.32, 10, 1.18, 8, 0.34,
              {'counter_shear_keep': 0.23, 'pad': 34, 'aperture': 17},
              {
                  'B': {'upper_bowl': 0.82, 'lower_bowl': 0.95, 'waist': 26, 'upper_hole': 0.68, 'lower_hole': 0.90},
                  'M': {'valley': 4, 'splay': 4},
                  'R': {'leg': -12, 'crotch': 16, 'upper_hole': 0.72},
                  'a': {'bar': 2, 'aperture': 16, 'hole': 0.78},
                  'g': {'aperture': 15, 'hole': 0.78, 'descender': -8},
                  'e': {'bar': 4, 'aperture': 18, 'hole': 0.86},
                  'two': {'base': 6, 'gap': 14},
                  'three': {'aperture': 16, 'upper_hole': 0.74, 'lower_hole': 0.90},
                  'six': {'aperture': 16, 'hole': 0.78},
                  'eight': {'upper_hole': 0.66, 'lower_hole': 0.90},
                  'nine': {'aperture': 16, 'hole': 0.78},
              }),
    900: _row(246, 228, 198, 0.20, 30, 1.02, 22, 0.26,
              {'counter_shear_keep': 0.30, 'pad': 42, 'aperture': 22},
              {
                  'B': {'upper_bowl': 0.76, 'lower_bowl': 0.93, 'waist': 32, 'upper_hole': 0.60, 'lower_hole': 0.86},
                  'M': {'valley': 12, 'splay': 8},
                  'R': {'leg': -16, 'crotch': 20, 'upper_hole': 0.64},
                  'a': {'bar': 4, 'aperture': 20, 'hole': 0.72},
                  'g': {'aperture': 18, 'hole': 0.74, 'descender': -4},
                  'e': {'bar': 6, 'aperture': 22, 'hole': 0.82},
                  'two': {'base': 8, 'gap': 18},
                  'three': {'aperture': 20, 'upper_hole': 0.66, 'lower_hole': 0.86},
                  'six': {'aperture': 20, 'hole': 0.74},
                  'eight': {'upper_hole': 0.58, 'lower_hole': 0.84},
                  'nine': {'aperture': 20, 'hole': 0.74},
              }),
}

FAMILIES = {'LihuiT': LIHUIT, 'zayJu': ZAYJU}

# 400 oblique does not retarget the approved drawing. These are only the
# slant-optical corrections, and they differ by family.
OBLIQUE_REGULAR = {
    'LihuiT': {'counter_shear_keep': 0.06, 'pad': 16, 'aperture': 3},
    'zayJu': {'counter_shear_keep': 0.08, 'pad': 14, 'aperture': 5},
}

for _family, _moves in {
    'LihuiT': {100: 1.22, 300: 1.08, 500: 0.80, 600: 0.68, 700: 0.56, 800: 0.48, 900: 0.40},
    'zayJu': {100: 1.30, 300: 1.12, 500: 0.72, 600: 0.58, 700: 0.46, 800: 0.38, 900: 0.30},
}.items():
    for _weight, _move in _moves.items():
        FAMILIES[_family][_weight]['counter_move'] = _move

RATIONALE = {
    'LihuiT': {
        100: '正文细体：竖茎压到约 34，横画仍留 26，接合故意重于茎（48）以免尖脚断开。B 的上碗仍小于下碗，腰部反而松开；M 的谷抬高，避免细线收成针尖。e 的横画上移、开口加大。字距明显放松。',
        300: '正文轻体：不是细体到 Regular 的中点。茎 58/48，仍比线性插值更轻，对比开始收回。B 的腰几乎回到参考，M 只轻轻抬谷。字距只加一点空气。',
        500: '正文中粗：竖茎 108、横画 94，比 Regular 暗一档，但横画追得更快，对比下降。B 上碗开始收、下碗保持，腰轻收。M 谷加深而不是简单加粗。字距略紧。',
        600: '正文半粗：调制指数降到 0.74，不再跟着 Regular 的粗细差走。接合与竖茎持平，开始给内白让路。B 腰明确内收，e 的开口被额外撑开，8 的下眼大于上眼。',
        700: '正文粗体：竖茎 150、接合只到 132，锐角内收形成轻微墨阱，而不是把 Regular 撑圆。字距比半粗回松，避免字字粘连。R 的腿缩短、裆部打开。与 zayJu 粗体相比仍更克制、更宽。',
        800: '特粗仍要能读：调制降到 0.40，内白下限是 Regular 的 0.42。M 的谷重新抬起，免得黑三角封死。字距转为正值。B 上眼明显小于下眼，这是比例决定，不是均匀内缩。',
        900: '黑体几乎单线（204/196），但 B 的上下碗、e 的开口、8 的上下眼仍保持不等。接合 174 轻于茎，内白下限 0.34。字距大幅放开。它不是特粗再加一圈。',
    },
    'zayJu': {
        100: '展示细体：对比明显高于 LihuiT（竖 28、横 16）。接合 42 托住发丝横画。B 的下眼比上眼更开，腰不收死。e 的横画抬得更高。M 仍是软谷，不是直线骨架。字距比 LihuiT 细体更紧。',
        300: '展示轻体：66/46，对比仍是展示体而不是 LihuiT 轻体的 58/48。R 的腿继续外甩。流动的腰刚刚开始出现。',
        500: '展示中粗：茎跳到 126，比 LihuiT 的 108 暗一截，横画仍明显更细（100）。B 的腰开始液体式内收，M 的谷挖深。这是两款在中段分叉最大的地方之一。',
        600: '展示半粗：腰收 14、M 谷再深，调制降到 0.66。字距是全家族最紧的一档（-18），因为这个重量的白还撑得住，再往上就要回松。',
        700: '展示粗体：184/160，接合只到 156。B 上眼缩到 0.74、下眼留 0.94，腰收 20。比 LihuiT 粗体更重、更收腰，也更需要斜体时的内白回正。',
        800: '展示特粗：茎 214，但内白下限降到 0.34，上眼继续让位给下眼。M 的谷从最深点往回抬，避免封口。字距重新打开。',
        900: '展示黑体：246/228，调制只留 0.20。B 上碗缩到 0.76、腰收 32，是整套里最强的收腰，同时开口和 8 的下眼被强制留白。字距 +30。它和 LihuiT 黑体不是同一个黑度。',
    },
}
