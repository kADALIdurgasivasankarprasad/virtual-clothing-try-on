import json
import os
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

app = FastAPI(title="Virtual Try-On Local Server")


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static") or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheMiddleware)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
PROXY_HEADERS = {"User-Agent": "VirtualTryOn-LocalServer"}


def load_colab_url():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("colab_url", "")
    return os.environ.get("COLAB_URL", "")


def save_colab_url(url):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"colab_url": url}, f)


COLAB_URL = load_colab_url().rstrip("/")


@app.post("/api/set-colab-url")
async def set_colab_url(request: Request):
    global COLAB_URL
    body = await request.json()
    COLAB_URL = body.get("url", "").rstrip("/")
    save_colab_url(COLAB_URL)
    return {"status": "ok", "colab_url": COLAB_URL}


@app.get("/api/get-colab-url")
async def get_colab_url():
    return {"colab_url": COLAB_URL}


@app.get("/api/health")
async def health_proxy():
    if not COLAB_URL:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Colab URL not configured"},
        )
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{COLAB_URL}/api/health", headers=PROXY_HEADERS
            )
            try:
                data = resp.json()
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={"status": "error", "detail": "Colab returned non-JSON response (tunnel may be starting up)"},
                )
            return JSONResponse(content=data, status_code=resp.status_code)
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Cannot connect to Colab"},
        )
    except httpx.ReadTimeout:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Colab health check timed out"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": f"Connection error: {type(e).__name__}"},
        )


@app.post("/api/try-on")
async def try_on_proxy(
    person_image: UploadFile = File(...),
    cloth_image: UploadFile = File(...),
    cloth_type: str = Form("upper"),
    num_inference_steps: int = Form(50),
    guidance_scale: float = Form(2.5),
    seed: int = Form(42),
):
    if not COLAB_URL:
        raise HTTPException(status_code=503, detail="Colab URL not configured")

    person_bytes = await person_image.read()
    cloth_bytes = await cloth_image.read()

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{COLAB_URL}/api/try-on",
                files={
                    "person_image": (
                        person_image.filename,
                        person_bytes,
                        person_image.content_type,
                    ),
                    "cloth_image": (
                        cloth_image.filename,
                        cloth_bytes,
                        cloth_image.content_type,
                    ),
                },
                data={
                    "cloth_type": cloth_type,
                    "num_inference_steps": str(num_inference_steps),
                    "guidance_scale": str(guidance_scale),
                    "seed": str(seed),
                },
                headers=PROXY_HEADERS,
            )
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503, detail="Cannot connect to Colab GPU server"
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504, detail="Colab inference timed out (>5min)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    print("Virtual Try-On Local Server")
    print(f"Colab URL: {COLAB_URL or '(not set - configure via frontend)'}")
    print("Open http://localhost:8090 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8090)
