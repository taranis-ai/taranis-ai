# Playwright guide

### Run tests and generate a video
*IMPORTANT: The tests are dependend on the `https://e2e.taranis.ai/e2e_test_db.sql` dump. Please restore it beforhand.* 

Example:
```bash
export TARANIS_URL="http://taranis" # Or wherever your version of Taranis is Running
python test_local_playwright.py
```

### To use Playwright Codegen tool, use `--save-storage` flag
```bash
playwright codegen localhost:8081 --save-storage=codegen_api_conf.json
```
