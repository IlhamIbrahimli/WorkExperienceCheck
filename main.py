from fastapi import FastAPI, Request, Form, Response, Depends, HTTPException, status, Header
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import hashlib
import datetime
from playwright.async_api import async_playwright

load_dotenv()
security = HTTPBasic()
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, os.environ.get("AUTH_USER"))
    correct_password = secrets.compare_digest(credentials.password, os.environ.get("AUTH_PASS"))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory="templates")

#supabase connection
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_TOKEN"))


async def get_page_hash(url: str) -> str:
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage","--disable-gpu",
        "--single-process"]
        )
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded", timeout=60000)
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["head", "script", "style", "nav", "header", "footer", "iframe",
                 "noscript", "svg", "img", "video", "audio", "canvas",
                 "form", "input", "button", "select", "textarea",
                 "aside", "figure", "figcaption", "picture", "source"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return hashlib.sha256(text.encode()).hexdigest()

@app.get("/links")
async def get_links(request: Request,credentials: HTTPBasicCredentials = Depends(authenticate)):
    response = supabase.table("experience").select("*").execute()
    experiences = response.data

    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "urls": experiences})

@app.get("/")
async def home(request: Request,credentials: HTTPBasicCredentials = Depends(authenticate)):
    return await get_links(request)


@app.post("/add_link")
async def add_link(request: Request, name: str = Form(), link: str = Form(), whenToApply: str = Form(None), credentials: HTTPBasicCredentials = Depends(authenticate)):
    response = supabase.table("experience").insert({"name": name, "link":link, "yearToApply": whenToApply}).execute()
    # return the _row.html partial, not the full page
    await check_link(response.data[0]["id"], x_secret_key=os.environ.get("CRON_SECRET"))
    return templates.TemplateResponse(request=Request, name="_row.html", context={"request": request, "url": response.data[0]})


@app.delete("/delete_link/{url_id}")
async def delete_link(request: Request,url_id: int, credentials: HTTPBasicCredentials = Depends(authenticate)):
    response = supabase.table("experience").delete().eq("id", url_id).execute()
    return Response(status_code=200)

@app.get("/check/{id}")
async def check_link(id: int, x_secret_key: str = Header(None)):#
    if x_secret_key != os.environ.get("CRON_SECRET"):
        raise HTTPException(status_code=401, detail="Unauthorised")
    response = supabase.table("experience").select("id, name, link, webHash, yearToApply").execute()
    links = response.data
    if id == 0:
        for i in range(len(links)):
            ts =datetime.datetime.now().isoformat()
            webHash = await get_page_hash(links[i]["link"])
            if links[i]["webHash"] == "":
                supabase.table("experience").update({"webHash": webHash,"lastCheck": ts}).eq("id", links[i]["id"]).execute()
            elif links[i]["webHash"] != webHash:
                supabase.table("experience").update({"webHash": webHash,"lastCheck": ts}).eq("id", links[i]["id"]).execute()
                requests.post(os.environ.get("NOTIFY_LINK"), data=f"{links[i]["name"]} role website status changed! You must apply in {links[i]["yearToApply"]}".encode(encoding='utf-8'))
    else:
        ts = datetime.datetime.now().isoformat()
        print(links)
        webHash = await get_page_hash(links[-1]["link"]) ## Will always be checking the last (most recent one)
        if links[-1]["webHash"] == "":
            supabase.table("experience").update({"webHash": webHash,"lastCheck": ts}).eq("id", id).execute()
        elif links[-1]["webHash"] != webHash:
            supabase.table("experience").update({"webHash": webHash,"lastCheck": ts}).eq("id", id).execute()
            requests.post(os.environ.get("NOTIFY_LINK"), data=f"{links[-1]["name"]} role website status changed! You must apply in {links[-1]["yearToApply"]}".encode(encoding='utf-8'))
        
    
        
    

