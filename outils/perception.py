"""Perception d'un personnage : ce qu'il voit, entend et remarque à chaque pas.

Ce que le personnage croit est séparé de ce qui est réel. Ses croyances sur
l'emplacement de ses objets ne changent que par ce qu'il fait lui-même (géré
par le moteur) ou par ce qu'il remarque (ici). Les règles sont dans la fiche,
section `perception`.

À chaque pas éveillé :
- il voit les pièces qu'il traverse (il y allume en passant) et la pièce où il
  se tient, si elle est éclairée ou s'il y fait jour ;
- il remarque un objet d'une pièce vue avec une probabilité qui dépend de
  l'attention (pièce où il se tient ou simple passage), de l'importance de
  l'objet et de sa concentration sur ce qu'il fait ; le tirage est
  déterministe (date, pas, objet) ;
- un objet remarqué ailleurs que là où il le croyait, ou absent de l'endroit
  où il le croyait, est une remarque : sa croyance est corrigée et
  l'événement correspondant est vécu ;
- il entend les appareils allumés à portée (pièce, pièces voisines ou tout
  le logement) ;
- il voit les personnes simulées présentes au même endroit.

Sans perturbation extérieure, ses croyances restent égales à la réalité : la
perception ne change alors rien à ce qu'il vit.
"""
import zlib


def tirage(*cle):
    """Nombre déterministe entre 0 et 1."""
    return (zlib.crc32("|".join(map(str, cle)).encode()) % 10000) / 10000


def piece_de(position, pieces):
    """Pièce du logement d'une position « pièce / support », ou None (objet porté, hors du logement)."""
    if not position:
        return None
    p = position.split(" / ", 1)[0]
    return p if p in pieces and " / " in position else None


class Perception:
    def __init__(self, fiche, sim):
        self.C = fiche["perception"]
        self.sim = sim
        self.importance = {o["id"]: o.get("importance", 0.5) for o in fiche["objets"]}
        self.voisines = {}
        for l in fiche["domicile"]["plan"]["liaisons"]:
            self.voisines.setdefault(l["a"], set()).add(l["b"])
            self.voisines.setdefault(l["b"], set()).add(l["a"])

    def visible(self, piece, i):
        """La pièce où il se tient est vue si elle est éclairée ou s'il y fait jour."""
        return self.sim.lumieres.get(piece) or not self.sim.besoin_lumiere(piece, i)

    def percevoir(self, i, lieu, piece, chemin, endormi, manipules):
        """Renvoie la perception du pas et les événements qu'elle fait vivre."""
        if endormi:
            return None, []
        sim, A = self.sim, self.C["attention"]
        P = sim.PIECES
        vues = {}
        for pc in chemin[:-1]:
            if pc in P:
                vues[pc] = A["passage"]
        if lieu == "domicile" and piece in P and self.visible(piece, i):
            vues[piece] = A["piece"]
        distraction = 1 - A["effet_concentration"] * sim.conc
        vu, remarques, evs = [], [], []
        for obj in sorted(sim.positions):
            if obj in manipules:
                continue
            reel, cru = sim.positions[obj], sim.croyances.get(obj)
            pr, pc = piece_de(reel, P), piece_de(cru, P)
            if pr not in vues and pc not in vues:
                continue
            p = max(vues.get(pr, 0), vues.get(pc, 0)) * (0.5 + 0.5 * self.importance.get(obj, 0.5)) * distraction
            if tirage(sim.date, i, obj, "vue") >= p:
                continue
            if pr in vues:
                vu.append(obj)
                if cru != reel:
                    remarques.append({"objet": obj, "type": "retrouve" if cru is None else "deplace", "croyait": cru, "voit": reel})
                    sim.croyances[obj] = reel
            elif cru is not None:
                remarques.append({"objet": obj, "type": "absent", "croyait": cru})
                sim.croyances[obj] = None
        for r in remarques:
            ev = self.C["evenements"]["retrouve" if r["type"] == "retrouve" else "deplace"]
            if ev not in evs:
                evs.append(ev)
        entend = []
        if lieu == "domicile" or (chemin and chemin[0] in P):
            ici = piece if piece in P else (chemin[0] if chemin else None)
            for app, spec in self.C["ouie"].items():
                if app not in sim.appareils:
                    continue
                ou = spec.get("piece") or ici
                portee = spec["portee"]
                if portee == "logement" or ou == ici or (portee == "voisines" and ici in self.voisines.get(ou, ())):
                    entend.append(spec["nom"])
        personnes = [x["nom"] for x in self.C.get("personnes", {}).get(lieu, [])]
        out = {k: v for k, v in (("vu", vu), ("entend", entend), ("personnes", personnes), ("remarques", remarques)) if v}
        return out or None, evs
