#!/usr/bin/env pybricks-micropython

from pybricks.tools import wait

from capteur_couleur import CapteurCouleur
from capteur_distance import CapteurDistance

ZONE = "zone"
PROXIMITE = "proximite"


class Evenements(object):
    def __init__(self, couleur=None, distance=None, proximite_mm=200):
        self.couleur = couleur
        self.distance = distance
        self.proximite_mm = proximite_mm
        self._zone = None
        self._proche = False
        self._pret = False
        self._handlers = {ZONE: [], PROXIMITE: []}

    def on(self, name, fn):
        self._handlers[name].append(fn)

    def _emit(self, name, *args):
        for fn in self._handlers[name]:
            fn(*args)

    def update(self):
        if self.couleur is not None:
            zone = self.couleur.zone()
            if self._pret and zone != self._zone:
                self._emit(ZONE, self._zone, zone)
            self._zone = zone

        if self.distance is not None:
            dist = self.distance.distance()
            proche = dist <= self.proximite_mm
            if self._pret and proche and not self._proche:
                self._emit(PROXIMITE, dist)
            self._proche = proche
   

        self._pret = True


if __name__ == "__main__":
    def sur_zone(avant, maintenant):
        print("zone {0} -> {1}".format(avant, maintenant))

    def sur_proximite(dist):
        print("proximite {0} mm".format(dist))

    ev = Evenements(CapteurCouleur(), CapteurDistance(), 200)
    ev.on(ZONE, sur_zone)
    ev.on(PROXIMITE, sur_proximite)
    while True:
        ev.couleur.refresh()
        ev.distance.refresh()
        ev.update()
        wait(100)
