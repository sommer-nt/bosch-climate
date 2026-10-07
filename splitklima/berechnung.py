"""Rechenkern CALC-0.4: Kühl- und Heizlast je Raum und für das Gebäude.

Kühllast: Abschätzung in Anlehnung an VDI 2078 Anhang D.
Heizlast: Bilanz in Anlehnung an DIN EN 12831-1.
Rechenweg identisch mit ``calcRoom``/``totals`` aus v6.9.1.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import parameter as P
from .modell import Einstellungen, Projekt, Raum


@dataclass
class RaumLast:
    cool: float  # kW netto
    cool_gross: float  # kW brutto
    storage_effect: float  # kW
    damp: float
    heat: float  # kW
    heat_trans: float
    heat_vent: float
    heat_reheat: float
    HT: float  # W/K
    HV: float  # W/K
    dUwb: float
    reheat_f: float
    wall_gross: float  # m²
    win: float  # m²
    roof_a: float
    floor_a: float
    ceil_a: float
    u_wall: float
    u_win: float
    g_val: float
    n: float
    solar: float  # W
    trans_c: float  # W
    vent_c: float  # W
    internal: float  # W


@dataclass
class GebaeudeLast:
    cool: float
    heat: float
    rooms: int
    raw_cool: float
    raw_heat: float
    sim_factor: float


def wand_u(raum: Raum, e: Einstellungen) -> float:
    d = P.RETROFIT.get(raum.daemmung)
    if d and d["u"] is not None:
        return d["u"]
    if raum.baualter in P.AGE_CLASSES:
        return P.AGE_CLASSES[raum.baualter]["w"]
    return P.USTD[e.daemmstandard]["w"]


def speicher_daempfung(raum: Raum, e: Einstellungen) -> float:
    sc = P.STORAGE_CLASS.get(raum.speicher, P.STORAGE_CLASS["mid"])
    h = e.kuehlbetrieb_h or 12
    f = 1.15 if h <= 6 else 1.0 if h <= 12 else 0.8 if h <= 18 else 0.6
    return min(0.35, sc["damp"] * f)


def luftwechsel(raum: Raum) -> float:
    return P.LUFTWECHSEL.get(raum.raumart, P.LUFTWECHSEL_DEFAULT)


def raum_last(raum: Raum, e: Einstellungen) -> RaumLast:
    A = raum.flaeche or 0.0
    h = raum.hoehe or 0.0
    dtC = e.sommer - e.soll_kuehlen_wirksam
    dtH = e.soll_heizen_wirksam - e.norm_aussen
    g = P.GLAS[e.verglasung]
    u = wand_u(raum, e)
    u_roof = u * 0.75
    shade_win = float(e.sonnenschutz)
    shade_roof = P.SHADE_ROOF.get(e.sonnenschutz, 1)

    win = win_wall = wg = solar_win = 0.0
    for w in raum.waende:
        wg += (w.laenge or 0) * h
        win += w.fenster or 0
        win_wall += w.fenster or 0
        solar_win += (w.fenster or 0) * P.SOL.get(w.ausrichtung, P.SOL_DEFAULT) * g["g"] * shade_win

    for gr in raum.fenstergruppen:
        ga = gr.flaeche or 0
        win += ga
        if not gr.dachfenster:
            win_wall += ga
        irr = P.DACHFENSTER_EINSTRAHLUNG if gr.dachfenster else P.SOL.get(gr.ausrichtung, P.SOL_DEFAULT)
        solar_win += ga * irr * g["g"] * (shade_roof if gr.dachfenster else shade_win)

    roof_a = (raum.dachflaeche or A) if raum.dach else 0.0
    solar_roof = roof_a * P.DACH_SOLAR.get(raum.dachform, 34) * shade_roof
    vf = P.VERTICAL.get(raum.vertikal, P.VERTICAL["between_heated"])
    floor_a = A if vf["floorU"] > 0 else 0.0
    ceil_a = A if vf["ceilU"] > 0 else 0.0
    opaque = max(0.0, wg - win_wall)

    # Kühllast
    vertical_c = floor_a * vf["floorU"] * dtC * vf["floorC"] + ceil_a * vf["ceilU"] * dtC * vf["ceilC"]
    trans_c = (opaque * u + win * g["u"] + roof_a * u_roof) * dtC + vertical_c
    V = A * h
    n = luftwechsel(raum)
    vent_c = 0.34 * n * V * dtC
    internal = (A * P.INTERN_W_M2_RAUMART.get(raum.raumart, P.INTERN_W_M2)
                + P.INTERN_GRUND.get(raum.raumart, P.INTERN_GRUND_DEFAULT))
    solar = solar_win + solar_roof
    cool_gross = solar + trans_c + vent_c + internal
    damp = speicher_daempfung(raum, e)
    storage_effect = cool_gross * damp
    cool_net = max(0.0, cool_gross - storage_effect)

    # Heizlast
    dUwb = P.WB_SURCHARGE.get(e.waermebruecken, P.WB_SURCHARGE["none"])["dU"]
    HT = (opaque * (u + dUwb) + roof_a * (u_roof + dUwb) + floor_a * vf["floorU"]
          + ceil_a * vf["ceilU"] + win * g["u"])
    HV = 0.34 * n * V
    phi_trans = HT * dtH
    phi_vent = HV * dtH
    phi_base = phi_trans + phi_vent
    reheat_f = P.REHEAT_FACTOR.get(e.aufheizreserve, P.REHEAT_FACTOR["none"])["f"]
    phi_reheat = phi_base * reheat_f

    return RaumLast(
        cool=cool_net / 1000, cool_gross=cool_gross / 1000, storage_effect=storage_effect / 1000,
        damp=damp, heat=(phi_base + phi_reheat) / 1000, heat_trans=phi_trans / 1000,
        heat_vent=phi_vent / 1000, heat_reheat=phi_reheat / 1000, HT=HT, HV=HV, dUwb=dUwb,
        reheat_f=reheat_f, wall_gross=wg, win=win, roof_a=roof_a, floor_a=floor_a, ceil_a=ceil_a,
        u_wall=u, u_win=g["u"], g_val=g["g"], n=n, solar=solar, trans_c=trans_c, vent_c=vent_c,
        internal=internal,
    )


def gebaeude_last(projekt: Projekt, betriebsart_beachten: bool = True) -> GebaeudeLast:
    """Summe aller Räume × Gleichzeitigkeit.

    Mit ``betriebsart_beachten`` wird – wie in der Oberfläche von v6.9.1 – bei
    „Nur Kühlen“ die Heizlast bzw. bei „Nur Heizen“ die Kühllast auf 0 gesetzt.
    """
    e = projekt.einstellungen
    cool = heat = 0.0
    for r in projekt.raeume:
        l = raum_last(r, e)
        cool += l.cool
        heat += l.heat
    f = e.gleichzeitigkeit_wirksam
    last = GebaeudeLast(cool * f, heat * f, len(projekt.raeume), cool, heat, f)
    if betriebsart_beachten:
        if e.betriebsart == "cool":
            last.heat = 0.0
        elif e.betriebsart == "heat":
            last.cool = 0.0
    return last
