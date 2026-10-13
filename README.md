# nexus-ops-ai — Gemelo Digital de Nexus Alarm

Gemelo digital de una empresa ficticia de instalación de alarmas en Ciudad de Buenos Aires (CABA).
Un enjambre de agentes opera el proceso comercial completo (lead → teleoperador → agenda → despacho
→ contrato → comprobante) y el dueño puede ver KPIs en vivo y probar escenarios "qué pasa si".

Cerebro del sistema: **modelo abierto servido vía TokenFactory sobre infraestructura AMD**
(`notebooks.amd.com/tokenfactory`). La inferencia de los agentes corre en AMD.

> **Proyecto de hackathon (AMD Developer Hackathon: ACT III / lablab.ai).**
> Todos los números, empresas y comprobantes son **SIMULADOS**. No constituyen asesoramiento,
> facturación real ni afirmaciones fiscales. La línea base de comparación es una **estimación**.

---

## Cómo correrlo (modo mock, sin gastar créditos)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
set USE_MOCK=true             # macOS/Linux: export USE_MOCK=true
uvicorn api.main:app --reload

# Frontend (cuando exista)
cd frontend
npm install
npm run dev
```

Con `USE_MOCK=true` todo el flujo funciona sin llamar a ningún modelo real.

##variables de entorno

Ver `.env.example`. Los secretos **nunca** se commitean.

## Arquitectura

```
Motor de eventos (determinista, sin LLM)
  reloj x120 · Monte Carlo · asignación de técnicos
        │
        ├── Teleoperador (LLM AMD)     califica lead, agenda, respeta "No Llame"
        ├── Despacho     (LLM AMD)     excepciones, reasignaciones
        ├── Contratos    (Evolus)      extractor + workflow, comprobante SIMULADO
        └── Panel dueño                KPIs, sliders, mapa, lead en vivo, métricas AMD
```

## Reglas del proyecto

- Salidas estructuradas: cada agente devuelve JSON validado con Pydantic (máx. 2 reintentos + fallback).
- Un único cliente LLM compatible con OpenAI (`base_url` configurable) → TokenFactory.
- Modo mock y caché/replay para reproducir la demo sin red.
- Métricas por llamada (latencia, tokens) expuestas al panel.

## Licencia

MIT. Ver `LICENSE`.
