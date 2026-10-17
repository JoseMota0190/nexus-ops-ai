"""Genera el mapa de CABA para el frontend a partir del GeoJSON oficial.

Uso:
    python scripts/build-caba-map.py <entrada.geojson> <salida.js>

Baja el detalle de más (Douglas-Peucker), redondea coordenadas y deja un módulo
JS liviano con los 48 barrios: nombre, comuna y los anillos de su polígono.
No es imprescindible correrlo de nuevo: el archivo generado ya está versionado.
"""
import json
import sys


def distancia_perpendicular(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def douglas_peucker(puntos, eps):
    if len(puntos) < 3:
        return list(puntos)
    a, b = puntos[0], puntos[-1]
    idx, dmax = 0, 0.0
    for i in range(1, len(puntos) - 1):
        d = distancia_perpendicular(puntos[i], a, b)
        if d > dmax:
            idx, dmax = i, d
    if dmax > eps:
        izq = douglas_peucker(puntos[: idx + 1], eps)
        der = douglas_peucker(puntos[idx:], eps)
        return izq[:-1] + der
    return [a, b]


def simplificar_anillo(anillo, eps):
    # El GeoJSON cierra el anillo repitiendo el primer punto: lo sacamos.
    if len(anillo) > 1 and anillo[0] == anillo[-1]:
        anillo = anillo[:-1]
    if len(anillo) < 4:
        return anillo
    # Simplificamos como línea abierta y volvemos a "cerrar" solo por convención.
    return douglas_peucker(anillo + [anillo[0]], eps)[:-1]


def anillos_de(geom):
    tipo = geom.get("type")
    coords = geom.get("coordinates") or []
    if tipo == "Polygon":
        return [coords]
    if tipo == "MultiPolygon":
        return coords
    return []


def main():
    entrada, salida = sys.argv[1], sys.argv[2]
    eps = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0004

    with open(entrada, encoding="utf-8") as f:
        data = json.load(f)

    barrios = []
    for feat in data["features"]:
        props = feat.get("properties", {})
        nombre = props.get("nombre") or props.get("barrio") or "?"
        comuna = props.get("comuna")
        anillos = []
        for poligono in anillos_de(feat["geometry"]):
            for anillo in poligono:  # 1er anillo = borde, resto = huecos
                limpio = simplificar_anillo(list(anillo), eps)
                if len(limpio) >= 3:
                    anillos.append([[round(lon, 5), round(lat, 5)] for lon, lat in limpio])
        if anillos:
            barrios.append({"nombre": nombre, "comuna": comuna, "anillos": anillos})

    barrios.sort(key=lambda b: b["nombre"])
    total = sum(len(a) for b in barrios for a in b["anillos"])

    with open(salida, "w", encoding="utf-8") as f:
        f.write("// GENERADO por scripts/build-caba-map.py — no editar a mano.\n")
        f.write("// Polígonos de los 48 barrios de CABA (coords [lon, lat], simplificados).\n")
        f.write("export const BARRIOS_CABA = ")
        f.write(json.dumps(barrios, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")

    print(f"OK: {len(barrios)} barrios, {total} puntos -> {salida}")


if __name__ == "__main__":
    main()
