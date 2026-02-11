# Virtual Try-On Studio

A web application that lets you virtually try on clothes using AI. Upload a photo of yourself and a garment image, and the app generates a realistic image of you wearing that garment.

Built with **CatVTON** (Concatenation Is All You Need for Virtual Try-On) running on a free Google Colab GPU, with a local web interface for easy use.

---

## How It Works

The app has two parts:

1. **Colab GPU Backend** - A Google Colab notebook that runs the CatVTON AI model on a free GPU and exposes it as an API through a Cloudflare tunnel.
2. **Local Web Server** - A lightweight FastAPI server on your computer that serves the web interface and proxies requests to the Colab backend.

```
Browser (localhost:8090)  -->  Local Server (FastAPI)  -->  Colab GPU (via Cloudflare tunnel)
```

This architecture lets you use a powerful GPU for free without installing heavy ML dependencies on your machine.

---

## Prerequisites

- **Python 3.8+** installed on your computer ([Download Python](https://www.python.org/downloads/))
- **A Google account** (for Google Colab)
- **A web browser** (Chrome, Edge, Firefox, etc.)

That's it. No GPU needed on your machine.

---

## Step-by-Step Setup

### Part 1: Start the Colab GPU Backend

1. **Open the Colab notebook**

   Go to [Google Colab](https://colab.research.google.com/) and upload the file:
   ```
   colab/CatVTON_API_Colab.ipynb
   ```
   Or if the project is on GitHub, click the "Open in Colab" button.

2. **Select a GPU runtime**

   In Colab, go to:
   ```
   Runtime  >  Change runtime type  >  Select "T4 GPU"  >  Save
   ```

3. **Run all cells**

   Click `Runtime > Run all` or press `Ctrl+F9`.

   The cells will:
   - Verify GPU is available
   - Clone the CatVTON repository and install dependencies (~2 minutes)
   - Download and load the AI model (~3 minutes)
   - Start the API server with a Cloudflare tunnel

4. **Copy the public URL**

   When the last cell finishes, you'll see output like:
   ```
   ============================================================
     API SERVER IS RUNNING!
     PUBLIC URL: https://some-random-words.trycloudflare.com
     Paste this URL into your local app!
   ============================================================
   ```
   Copy this URL. You'll paste it into the web app.

> **Note:** The Cloudflare tunnel URL changes every time you restart the notebook. Colab sessions also time out after a period of inactivity, so keep the tab open.

---

### Part 2: Start the Local Web Server

1. **Open a terminal / command prompt**

   Navigate to the project folder:
   ```bash
   cd "path/to/virtual try on"
   ```

2. **Install dependencies** (only needed once)

   ```bash
   pip install -r requirements-local.txt
   ```

   This installs:
   - `fastapi` - web framework
   - `uvicorn` - ASGI server
   - `httpx` - HTTP client for proxying to Colab
   - `python-multipart` - for file uploads

3. **Start the server**

   ```bash
   python server.py
   ```

   You should see:
   ```
   Virtual Try-On Local Server
   Colab URL: (not set - configure via frontend)
   Open http://localhost:8090 in your browser
   ```

4. **Open the web app**

   Go to [http://localhost:8090](http://localhost:8090) in your browser.

---

### Part 3: Use the App

1. **Paste the Colab URL**

   In the top bar of the web app, paste the Cloudflare tunnel URL you copied from Colab and click the arrow button (or press Enter).

   The status pill should change from red "Disconnected" to green "Connected - Tesla T4".

2. **Upload a person photo**

   Click the "Your Photo" panel and upload a full-body photo. Tips:
   - Use a clear, front-facing full-body photo
   - Good lighting helps
   - Simple backgrounds work better

3. **Upload a garment image**

   Click the "Garment" panel and upload a clothing image. Tips:
   - Flat lay photos on white/plain backgrounds work best
   - Product photos from shopping sites work great
   - Make sure the garment is clearly visible

4. **Select garment type**

   Choose one of:
   - **Upper** - tops, shirts, jackets, etc.
   - **Lower** - pants, skirts, shorts, etc.
   - **Full Body** - dresses, jumpsuits, etc.

5. **Click "Generate Try-On"**

   The app sends images to the Colab GPU for processing. This takes about **30-60 seconds**.

6. **View and download results**

   The result appears as a side-by-side comparison. Click "Download" to save it.

---

## Project Structure

```
virtual try on/
├── colab/
│   └── CatVTON_API_Colab.ipynb   # Colab notebook (GPU backend)
├── static/
│   ├── index.html                  # Web app HTML
│   ├── style.css                   # Styles
│   └── app.js                      # Frontend JavaScript
├── server.py                       # Local FastAPI proxy server
├── requirements-local.txt          # Python dependencies
├── config.json                     # Stores the last used Colab URL (auto-generated, gitignored)
└── README.md                       # This file
```

---

## Troubleshooting

### "Disconnected" or "Not connected"

- Make sure the Colab notebook is still running (check the Colab tab)
- The Cloudflare tunnel URL changes every restart - copy the new one
- Cloudflare tunnels can be briefly unstable; the app retries automatically every 30 seconds

### "Colab returned non-JSON response"

- The Cloudflare tunnel is starting up. Wait 10-20 seconds and it should connect.
- If it persists, restart the last cell in the Colab notebook to get a new tunnel URL.

### Processing takes too long

- Normal processing time is 30-60 seconds on a T4 GPU
- If it takes longer, the Colab instance may be under heavy load
- Check the Colab notebook for any error messages

### Colab session disconnected

- Free Colab sessions timeout after ~90 minutes of inactivity
- If disconnected, click `Runtime > Run all` in Colab again and paste the new URL

### "Colab URL not configured"

- You need to paste the Cloudflare tunnel URL from Colab into the top bar of the web app and click connect

### Local server won't start

- Make sure Python 3.8+ is installed: `python --version`
- Make sure dependencies are installed: `pip install -r requirements-local.txt`
- Make sure port 8090 is not in use by another application

---

## How It Works (Technical)

1. The **Colab notebook** loads the CatVTON model (a diffusion-based virtual try-on model) and runs a FastAPI server on port 8000, exposed via a Cloudflare tunnel.

2. The **local server** (`server.py`) serves the web frontend and proxies API calls to Colab. This avoids CORS issues and lets you configure the Colab URL easily.

3. When you click "Generate Try-On":
   - Your images are sent to the local server
   - The local server forwards them to the Colab GPU backend
   - CatVTON generates an automatic mask for the clothing region using DensePose
   - The diffusion model generates the try-on result at 768x1024 resolution
   - The result image is sent back as a base64-encoded PNG

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the web app |
| `/api/health` | GET | Checks if Colab backend is connected |
| `/api/get-colab-url` | GET | Returns the currently configured Colab URL |
| `/api/set-colab-url` | POST | Sets a new Colab URL |
| `/api/try-on` | POST | Sends images for virtual try-on |

---

## Credits

- **CatVTON** - [Zheng-Chong/CatVTON](https://github.com/Zheng-Chong/CatVTON) - The AI model powering virtual try-on
- **Stable Diffusion Inpainting** - Base model used by CatVTON
- **Cloudflare Tunnels** - Free tunneling service for exposing the Colab API
