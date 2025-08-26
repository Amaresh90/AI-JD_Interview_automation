# Steps
1. Install python and uv package
2. clone the repository 
3. Create virtual environment
`uv venv .` 
4. Activating the virtual environment 
* macOS & linux 
`source .venv\bin\activate`
* windows (powershell)
`. .venv/Scripts/activate`
5. Run
 `uvicorn main:app --reload --port <port>`
  `eg: uvicorn main:app --reload --port 8080`
  