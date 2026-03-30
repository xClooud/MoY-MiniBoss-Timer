import math


def HardDef(baseDmg, Hdef, reducaoFlat=0, reducaoPercent=0):
    finalHdef = (Hdef - reducaoFlat) * (1 - reducaoPercent / 100)
    danoFinal = baseDmg * ((4000 + finalHdef) / (4000 + finalHdef * 10))
    print(
        f"Dano Final: {danoFinal:.2f}, Redução: {100 - (danoFinal / baseDmg * 100):.2f}%"
    )
    return danoFinal


def HardMdef(baseDmg, Mdef, reducaoFlat, reducaoPercent):
    finalMdef = (Mdef - reducaoFlat) * (1 - reducaoPercent / 100)
    danoFinal = baseDmg * ((1000 + finalMdef) / (1000 + finalMdef * 10))
    print(
        f"Dano Final: {danoFinal:.2f}, Redução: {100 - (danoFinal / baseDmg * 100):.2f}%"
    )
    return danoFinal


def VariableCast(base, reducaoFlat, reducaoPercent, int, dex):
    stat = 1 - (((dex * 2) + int) / 470)
    rate = 1 - (reducaoPercent / 100)
    vctFinal = (base * stat * rate) - reducaoFlat
    return max(vctFinal, 0)


def BlitzBeat(baseDmg, skillLvl, baseLvl):
    dmg = 100 + (skillLvl * 30) + (baseLvl * 3)
    dmg = baseDmg * (dmg / 100)
    return dmg


print(BlitzBeat(187, 10, 100))
