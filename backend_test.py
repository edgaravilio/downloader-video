import requests
import time

BASE_URL = "http://localhost:8081/api"

def test_backend_e2e():
    print("--- Probando Backend E2E ---")
    
    # 1. Probar Análisis de URL válida
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"1. Analizando URL: {url}")
    try:
        res = requests.post(f"{BASE_URL}/analyze", json={"url": url, "process_playlist": False})
        if res.status_code == 200:
            data = res.json()
            print(f"   [OK] Título: {data.get('title')}")
            print(f"   [OK] Formatos encontrados: {len(data.get('formats', []))}")
            
            # 2. Probar Inicio de Descarga
            format_id = data['formats'][0]['id']
            print(f"2. Iniciando descarga: {format_id}")
            res_dl = requests.post(f"{BASE_URL}/download", json={
                "url": url,
                "format_id": format_id,
                "title": data.get('title')
            })
            if res_dl.status_code == 200:
                download_id = res_dl.json().get('download_id')
                print(f"   [OK] ID Descarga: {download_id}")
                
                # 3. Monitorear progreso por unos segundos
                print("3. Monitoreando progreso...")
                for _ in range(5):
                    res_st = requests.get(f"{BASE_URL}/status/{download_id}")
                    if res_st.status_code == 200:
                        st_data = res_st.json()
                        print(f"   Estado: {st_data.get('status')} | Progreso: {st_data.get('progress')}% | Msg: {st_data.get('message')}")
                    time.sleep(2)
                
                # 4. Cancelar descarga
                print("4. Cancelando descarga...")
                requests.post(f"{BASE_URL}/cancel/{download_id}")
                res_st = requests.get(f"{BASE_URL}/status/{download_id}")
                print(f"   [OK] Estado final: {res_st.json().get('status')}")
            else:
                print(f"   [FALLO] Inicio descarga: {res_dl.status_code} - {res_dl.text}")
        else:
            print(f"   [FALLO] Análisis: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"   [ERROR] Excepción: {e}")

    # 5. Probar URL Inválida
    print("\n5. Probando URL Inválida...")
    res_inv = requests.post(f"{BASE_URL}/analyze", json={"url": "invalid_url"})
    print(f"   Respuesta: {res_inv.status_code} - {res_inv.text}")

if __name__ == "__main__":
    test_backend_e2e()
