import streamlit as st
import pandas as pd
from datetime import datetime, date
import re
import io
import os
import json
import unicodedata
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from supabase import create_client, Client

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Sievert | Ingreso", 
    page_icon="☢️", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- GESTIÓN DE SECRETOS ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GMAIL_USER = st.secrets.get("GMAIL_USER", "")
    GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD", "")
    EMAIL_DESTINO_INTERNO = st.secrets.get("EMAIL_DESTINO_INTERNO", GMAIL_USER)
except:
    SUPABASE_URL = ""; SUPABASE_KEY = ""; GMAIL_USER = ""; GMAIL_PASSWORD = ""; EMAIL_DESTINO_INTERNO = ""

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    else: supabase = None
except: supabase = None

# --- CARGAR DATOS COLOMBIA ---
@st.cache_data
def cargar_datos_colombia():
    archivo = "ciudades.csv"
    bkp = {"BOGOTA D.C.": ["BOGOTA D.C."], "ANTIOQUIA": ["MEDELLIN"]}
    if not os.path.exists(archivo): return bkp
    try:
        try: df = pd.read_csv(archivo, sep=";", encoding='utf-8')
        except: df = pd.read_csv(archivo, sep=";", encoding='latin-1')
        cols = {'Nombre Departamento', 'Nombre Municipio'}
        if not cols.issubset(df.columns): return bkp
        df = df.apply(lambda x: x.astype(str).str.upper())
        return {k: sorted(g['Nombre Municipio'].tolist()) for k, g in df.groupby('Nombre Departamento')}
    except: return bkp

COLOMBIA_DATA = cargar_datos_colombia()
DEPARTAMENTOS = sorted(list(COLOMBIA_DATA.keys()))

# --- LISTAS MAESTRAS ---
LISTAS = {
    "TIPO_DOC": ["CC", "CE", "TI", "PA (PASAPORTE)", "PEP", "PPT"],
    "NIVEL_EDUCATIVO": ["PRIMARIA", "SECUNDARIA", "TECNICO", "TECNOLOGO", "PROFESIONAL", "ESPECIALISTA", "MAGISTER", "DOCTORADO"],
    "TITULO": ["MIEMBROS FUERZAS MILITARES, POLICIA", "DIRECTORES, GERENTES Y PERSONAL ADMINISTRATIVO", "FISICOS", "FISICOS MEDICOS", "MEDICOS GENERALES", "MEDICOS ESPECIALISTAS", "MEDICOS NUCLEARES", "MEDICOS RADIONCOLOGOS", "MEDICOS RADIOLOGOS", "TECNICOS Y TECNOLOGOS EN IMAGENES DIAGNOSTICAS", "TECNICOS EN TECNOLOGOS EN RADIOTERAPIA", "TECNICOS Y TECNOLOGOS EN MEDICINA NUCLEAR", "OTROS TECNICOS Y TECNOLOGOS EN SALUD", "ODONTOLOGOS", "PROFESIONALES DE ENFERMERIA", "TECNICOS Y PROFESIONALES DEL NIVEL MEDIO DE ENFERMERIA", "PARAMEDICOS E INSTRUMENTADORES QUIRURGICOS", "OTROS PROFESIONALES DE LA SALUD", "VETERINARIOS", "TECNICOS Y ASISTENTES VETERINARIOS", "PROFESIONALES DE LA INGENIERIA", "QUIMICOS Y QUIMICOS FARMACEUTICOS", "PROFESIONALES DE LAS CIENCIAS NATURALES", "PROFESIONALES DE LA PROTECCION MEDIOAMBIENTAL", "DOCENTES E INVESTIGADORES", "TECNICOS Y TECNOLOGOS EN CIENCIAS NATURALES E INGENIERIA", "TECNICOS Y CONTROLADORES EN NAVEGACION MARITIMA Y AERONAUTICA", "FUNCIONARIOS E INSPECTORES GUBERNAMENTALES", "EMPLEADOS TRANSPORTE MATERIAL RADIACTIVO", "BOMBEROS", "MINEROS", "OBREROS MINAS", "OPERADORES PORTUARIOS", "OTROS TRABAJADORES INDUSTRIALES", "OTROS TRABAJADORES NIVEL TECNICO"],
    "OCUPACION": ["MEDICO RADIOLOGO" ,"MEDICO CARDIOLOGO", "MEDICO ONCOLOGO", "MEDICO NUCLEAR", "MEDICO CIRUJANO", "MEDICO HEMODINAMISTA", "NEUROCIRUJANO", "CIRUJANO VASCULAR", "RESIDENTE", "ORTOPEDISTA", "ANESTESIOLOGO", "INSTRUMENTADOR QUIRURGICO", "JEFE ENFERMERIA", "AUX. ENFERMERIA", "TEC. EN IMAGENES", "TRANCRIPTOR", "ODONTOLOGO", "PERIODONCISTA", "ENDODONCISTA", "AUX. ODONTOLOGIA", "HIGIENE ORAL", "ING. BIOMEDICO", "FISICO MEDICO", "DOCENCIA", "INVESTIGACION", "OTRO"],
    "AREA": ["RADIOLOGIA", "HEMODINAMIA", "CIRUGIA", "ODONTOLOGIA", "MEDICINA NUCLEAR", "RADIOTERAPIA", "VETERINARIA", "INDUSTRIA EQUIPOS", "INDUSTRIA FUENTES", "OTRO"],
    "COBERTURA": ["ARL","PARTICULAR"],
    "TECNOLOGIA": ["TLD", "OSL", "DIS"],
    "UBICACION_CORPO": ["TORAX (CUERPO ENTERO)", "CRISTALINO", "ANILLO", "FETAL", "ZONA CONTROLADA", "ZONA SUPERVISADA"],
    "PERIODICIDAD": ["MENSUAL", "BIMENSUAL", "TRIMESTRAL"],
    "GENERO": ["FEMENINO", "MASCULINO", "OTRO"],
    "MESES": ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
}

# --- ESTILOS CSS ---
def inyectar_estilos():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700&display=swap');
        :root { --primary: #002060; --secondary: #58207C; --bg-page: #f4f7f9; --bg-card: #ffffff; --text-main: #2c3e50; }
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: var(--bg-page); color: var(--text-main); }
        .header-title { color: var(--primary); font-weight: 700; font-size: 1.8rem; margin: 0; }
        .status-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; margin-right: 12px; min-width: 140px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
        .status-ok { background-color: #d1e7dd; color: #0f5132; border: 1px solid #badbcc; }
        .status-err { background-color: #f8d7da; color: #842029; border: 1px solid #f5c2c7; }
        div[data-testid="stVerticalBlock"] > div[style*="background-color"] { background-color: var(--bg-card); border: 1px solid #e0e6ed; border-radius: 12px; padding: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.02); }
        .stButton > button { background-color: var(--primary); color: white; border-radius: 50px; padding: 0.5rem 1.5rem; font-weight: 600; border: none; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,32,96,0.1); }
        .stButton > button:hover { background-color: var(--secondary); transform: translateY(-1px); color: white; }
        button[kind="secondary"] { background-color: white; border: 1px solid var(--primary); color: var(--primary); box-shadow: none; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stDateInput input { background-color: #fff; border: 1px solid #ced4da; border-radius: 8px; padding: 8px; text-transform: uppercase; font-size: 0.9rem; }
        .stTextInput input:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(0,32,96,0.1); }
        .stDataFrame { width: 100% !important; }
        .footer { text-align: center; font-size: 0.75rem; color: #bdc3c7; margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; }
        header[data-testid="stHeader"] { display: none; }
        .block-container { padding-top: 1rem; max-width: 98%; }
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
    """, unsafe_allow_html=True)
inyectar_estilos()

# --- ESTADO ---
if 'cliente' not in st.session_state: st.session_state.cliente = {"razon_social": "", "nit": "", "responsable": "", "cargo": "", "email": "", "telefono": "", "direccion": "", "municipio": "", "departamento": ""}
if 'sedes' not in st.session_state: st.session_state.sedes = []
if 'usuarios' not in st.session_state: st.session_state.usuarios = []
if 'last_sede' not in st.session_state: st.session_state.last_sede = None
if 'last_area' not in st.session_state: st.session_state.last_area = None

# --- FUNCIONES ---
def limpiar_texto(texto):
    if pd.isna(texto) or texto is None: return ""
    texto = str(texto).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def validar_email(email):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", str(email)) is not None

def get_primer_dia_mes(mes_nombre, anio):
    try: return date(anio, LISTAS["MESES"].index(mes_nombre.upper()) + 1, 1)
    except: return date.today().replace(day=1)

def verificar_estado_general():
    cli = st.session_state.cliente
    cli_ok = True if cli["razon_social"] else False
    sed_ok = len(st.session_state.sedes) > 0
    return cli_ok, sed_ok

def validar_tabla_usuarios_estricta():
    usuarios = st.session_state.usuarios
    if not usuarios: return False, "⚠️ Tabla vacía."
    for i, u in enumerate(usuarios):
        f = i + 1
        for k in ["Nombres", "Apellidos", "Documento", "Correo", "Sede", "Ubicaciones"]:
            if not u.get(k) or str(u.get(k)).strip() == "": return False, f"⛔ Fila {f}: Falta '{k}'."
        if not validar_email(u.get("Correo")): return False, f"⛔ Fila {f}: Email inválido."
        if u.get("Area") == "OTRO" and not u.get("Otra Area"): return False, f"⛔ Fila {f}: Falta 'Otra Area'."
    return True, "OK"

# --- 📧 GMAIL SMTP ---
def enviar_correo_gmail(destinatario, asunto, cuerpo_html, archivos_adjuntos=[]):
    """Retorna (Exito: bool, Mensaje: str)"""
    if not GMAIL_USER or not GMAIL_PASSWORD: 
        return False, "Faltan credenciales de Gmail en secrets.toml"
    
    msg = MIMEMultipart()
    msg['From'] = f"Sievert Dosimetría <{GMAIL_USER}>"
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo_html, 'html'))

    if archivos_adjuntos:
        for nombre_archivo in archivos_adjuntos:
            try:
                if os.path.exists(nombre_archivo):
                    with open(nombre_archivo, "rb") as f:
                        part = MIMEApplication(f.read(), Name=nombre_archivo)
                    part['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
                    msg.attach(part)
                else: print(f"⚠️ Archivo no encontrado: {nombre_archivo}")
            except Exception as e: print(f"Error adjuntando: {e}")

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, destinatario, msg.as_string())
        server.quit()
        return True, "Enviado correctamente"
    except Exception as e:
        return False, f"Error SMTP: {str(e)}"

def procesar_notificaciones(cliente, n_sedes, n_usuarios):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    errores = []
    
    # 1. Alerta Interna
    html_interno = f"""
    <div style="font-family: Arial; color: #333;">
        <h2 style="color: #d9534f;">⚠️ ACCIÓN REQUERIDA: Creación nuevo cliente</h2>
        <p>Pendiente de validación en plataforma.</p>
        <ul>
            <li><b>Cliente:</b> {cliente['razon_social']}</li>
            <li><b>NIT:</b> {cliente['nit']}</li>
            <li><b>Servicios:</b> {n_usuarios}</li>
            <li><b>Sedes:</b> {n_sedes}</li>
        </ul>
    </div>
    """
    ok_int, msg_int = enviar_correo_gmail(EMAIL_DESTINO_INTERNO, f"🔔 Ingreso: {cliente['razon_social']}", html_interno)
    if not ok_int: errores.append(f"Fallo correo interno: {msg_int}")

    # 2. Bienvenida Cliente
    if validar_email(cliente['email']):
        # Limpieza de NIT para credenciales
        nit_limpio = re.sub(r'\D', '', str(cliente['nit']))
        
        html_cliente = f"""
        <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
            <div style="background-color: #002060; padding: 25px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">¡Bienvenido a Sievert S.A.S!</h1>
                <p style="color: #e0e0e0; margin: 5px 0 0; font-size: 14px;">Expertos en Protección Radiológica</p>
            </div>
            
            <div style="padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
                <p style="font-size: 16px;">Hola <b>{cliente['responsable']}</b>,</p>
                <p>Es un gusto saludarte. Confirmamos que hemos recibido exitosamente la información de tu personal ({n_usuarios} usuarios) para el inicio del servicio.</p>

                <div style="background-color: #f0f7ff; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 5px solid #002060;">
                    <h3 style="color: #002060; margin-top: 0; font-size: 18px;">🔐 Tus Credenciales de Acceso</h3>
                    <p style="margin-bottom: 15px;">Ya puedes ingresar a nuestra plataforma de gestión de dosimetría:</p>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 6px; text-align: center; border: 1px solid #ddd;">
                        <p style="margin: 5px; font-size: 15px;">👤 <b>Usuario:</b> <span style="font-family: monospace; font-size: 16px; color: #002060;">{nit_limpio}</span></p>
                        <p style="margin: 5px; font-size: 15px;">🔑 <b>Contraseña:</b> <span style="font-family: monospace; font-size: 16px; color: #002060;">{nit_limpio}</span></p>
                    </div>

                    <div style="text-align: center; margin-top: 20px;">
                        <a href="https://dosimetria.sievert.com.co/" style="background-color: #002060; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; display: inline-block; font-size: 14px;">Ingresar al Software</a>
                    </div>
                </div>

                <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 5px solid #ffc107;">
                    <h3 style="color: #856404; margin-top: 0; font-size: 18px;">☢️ El Dosímetro de Control es Vital</h3>
                    <p style="font-size: 14px; color: #856404; margin-bottom: 10px;">
                        Con el envío de los dosímetros personales, recibirás un <b>Dosímetro de Control</b>. Este permite registrar la dosis no ocupacional (transporte y almacenamiento) y es indispensable para el análisis correcto.
                    </p>
                    <ul style="font-size: 14px; color: #856404; padding-left: 20px;">
                        <li>📍 <b>Ubicación:</b> Guárdalo lejos del equipo de Rayos X (fuera de la sala).</li>
                        <li>📦 <b>Devolución:</b> Envíalo de regreso junto con los dosímetros personales de cada periodo.</li>
                        <li>🚫 <b>Uso:</b> NUNCA lo asignes a una persona.</li>
                    </ul>
                </div>

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <h4 style="color: #002060; margin: 0 0 10px 0;">📋 Política de Devolución y Pérdida</h4>
                    <p style="font-size: 13px; color: #666; line-height: 1.5;">
                        La devolución oportuna de los dosímetros es necesaria para el cumplimiento normativo. Recuerda que la pérdida, daño o no devolución de los equipos genera costos de reposición. Te invitamos a revisar la <b>Política de Cartera</b> adjunta (Imagen) para más detalles.
                    </p>
                </div>
                
                <p style="margin-top: 30px; font-size: 14px; color: #555;">
                    Cualquier inquietud técnica, estoy a tu disposición:<br>
                    <b>Diego Orjuela</b> - Coordinador Técnico<br>
                    <a href="mailto:diego@sievert.com.co" style="color: #002060;">diego@sievert.com.co</a> | +57 318 3731885
                </p>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 11px; color: #999; border-radius: 0 0 8px 8px;">
                <p>Sievert S.A.S - Protección Radiológica<br>Medellín, Colombia | <a href="https://www.sievert.com.co" style="color: #999;">www.sievert.com.co</a></p>
            </div>
        </div>
        """
        
        ok_cli, msg_cli = enviar_correo_gmail(
            cliente['email'], 
            "✨ Bienvenida al servicio de dosimetría - Sievert S.A.S", 
            html_cliente,
            archivos_adjuntos=["Política_Cartera.jpg"]
        )
        if not ok_cli: errores.append(f"Fallo correo cliente: {msg_cli}")
    
    return errores

# --- GUARDADO BD ---
def guardar_en_base_datos(cliente, sedes, usuarios):
    if not supabase: return False, "Sin conexión a BD."
    try:
        # Guardar Cliente
        data_cli = {
            "razon_social": cliente["razon_social"], "nit": cliente["nit"],
            "email": cliente["email"], "telefono": cliente["telefono"],
            "responsable": cliente["responsable"], "cargo_responsable": cliente["cargo"],
            "direccion": cliente["direccion"], "departamento": cliente["departamento"],
            "municipio": cliente["municipio"]
        }
        res_cli = supabase.table("clientes").insert(data_cli).execute()
        cid = res_cli.data[0]['id']

        # Guardar Sedes
        map_sid = {} 
        for s in sedes:
            res_s = supabase.table("sedes").insert({
                "cliente_id": cid, "nombre": s["nombre"], "direccion": s["direccion"],
                "departamento": s["departamento"], "municipio": s["municipio"],
                "responsable": s["responsable"], "email": s["email"], "telefono": s["telefono"]
            }).execute()
            map_sid[s["nombre"]] = res_s.data[0]['id']

        # Guardar Usuarios
        chunk = 100
        ubd = []
        for u in usuarios:
            sid = map_sid.get(u["Sede"])
            if sid:
                ubd.append({
                    "sede_id": sid, "nombres": u["Nombres"], "apellidos": u["Apellidos"],
                    "tipo_doc": u["Tipo Doc"], "documento": u["Documento"],
                    "email": u["Correo"], "fecha_nacimiento": u["F. Nacimiento"],
                    "genero": u["Genero"], "nivel_educativo": u["Nivel"],
                    "titulo": u["Titulo"], "ocupacion": u["Ocupacion"],
                    "area": u["Area"], "otra_area": u.get("Otra Area", ""),
                    "cobertura": u["Cobertura"], "tecnologia": u["Tecnologia"],
                    "periodicidad": u["Periodicidad"], "ubicaciones": u["Ubicaciones"],
                    "fecha_inicio": u["F. Inicio"]
                })
        
        for i in range(0, len(ubd), chunk):
            supabase.table("usuarios").insert(ubd[i:i+chunk]).execute()
            
        # --- ENVIAR CORREOS Y CAPTURAR ERRORES ---
        lista_errores = procesar_notificaciones(cliente, len(sedes), len(usuarios))
        
        if lista_errores:
            return True, f"Datos guardados, pero hubo errores de correo: {'; '.join(lista_errores)}"
        
        return True, "OK"
        
    except Exception as e: return False, str(e)

# --- EXCEL ---
def generar_plantilla_excel():
    cols = ["Nombres", "Apellidos", "Tipo Doc", "Documento", "Correo", "F. Nacimiento (YYYY-MM-DD)", "Genero", "Nivel Educativo", "Titulo", "Ocupacion", "Area", "Otra Area", "Sede", "Cobertura", "Tecnologia", "Periodicidad", "Ubicaciones", "Mes Inicio", "Año Inicio"]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df = pd.DataFrame(columns=cols); df.to_excel(writer, index=False, sheet_name='Plantilla')
        wb, ws = writer.book, writer.sheets['Plantilla']; wr = wb.add_worksheet('Listas')
        sn = [s["nombre"] for s in st.session_state.sedes] if st.session_state.sedes else ["Sin Sedes"]
        
        cf = [(2,"D",LISTAS["TIPO_DOC"]),(6,"G",LISTAS["GENERO"]),(7,"N",LISTAS["NIVEL_EDUCATIVO"]),(8,"T",LISTAS["TITULO"]),(9,"O",LISTAS["OCUPACION"]),(10,"A",LISTAS["AREA"]),(12,"S",sn),(13,"L_COB",LISTAS["COBERTURA"]),(14,"TE",LISTAS["TECNOLOGIA"]),(15,"P",LISTAS["PERIODICIDAD"]),(17,"M",LISTAS["MESES"])]
        
        for i, (ci, n, d) in enumerate(cf):
            wr.write(0, i, n); [wr.write(j+1, i, v) for j,v in enumerate(d)]
            l = chr(ord('A')+i); wb.define_name(n, f'=Listas!${l}$2:${l}${len(d)+1}')
            ws.data_validation(1, ci, 1000, ci, {'validate':'list','source':f'={n}'})
        ws.data_validation(1, 5, 1000, 5, {'validate':'date','criteria':'between','minimum':date(1930,1,1),'maximum':date.today()})
        ws.write_comment('Q1', "Puede poner varias separadas por comas. Ej: TORAX, ANILLO")
        wr.hide(); ws.set_column('A:S', 20)
    buffer.seek(0); return buffer

def procesar_excel_masivo(file):
    try: df = pd.read_excel(file)
    except Exception as e: return None, [f"Error archivo: {str(e)}"]
    df.columns = [c.strip() for c in df.columns]
    sm = {limpiar_texto(s["nombre"]): s["nombre"] for s in st.session_state.sedes}
    if not sm: return None, ["Cree al menos una sede."]
    err, pro = [], []
    for i, r in df.iterrows():
        f = i + 2
        nm, ap = limpiar_texto(r.get("Nombres")), limpiar_texto(r.get("Apellidos"))
        dc = str(r.get("Documento")).split('.')[0]
        sd = limpiar_texto(r.get("Sede"))
        ar, oa = limpiar_texto(r.get("Area")), limpiar_texto(r.get("Otra Area"))
        if ar == "OTRO" and not oa: err.append(f"Fila {f}: Falta 'Otra Area'"); continue
        if not nm or not ap: err.append(f"Fila {f}: Falta Nombre/Apellido"); continue
        if not dc or dc == "nan": err.append(f"Fila {f}: Falta Documento"); continue
        rs = sm.get(sd)
        if not rs: err.append(f"Fila {f}: Sede '{r.get('Sede')}' no existe."); continue
        fn = str(r.get("F. Nacimiento (YYYY-MM-DD)")).split()[0]
        fi = get_primer_dia_mes(limpiar_texto(r.get("Mes Inicio")), r.get("Año Inicio"))
        ub = str(r.get("Ubicaciones")).upper()
        if ub in ["NAN", "NONE", ""]: err.append(f"Fila {f}: Falta Ubicación"); continue
        for ubic in [u.strip() for u in ub.replace(';',',').split(',') if u.strip()]:
            pro.append({
                "Nombres":nm,"Apellidos":ap,"Tipo Doc":r.get("Tipo Doc"),"Documento":dc,"Correo":str(r.get("Correo")).lower(),
                "F. Nacimiento":fn,"Genero":str(r.get("Genero")).upper(),"Nivel":str(r.get("Nivel Educativo")).upper(),"Titulo":str(r.get("Titulo")).upper(),
                "Ocupacion":str(r.get("Ocupacion")).upper(),"Area":ar,"Otra Area":oa,"Sede":rs,
                "Cobertura":str(r.get("Cobertura")).upper(),"Tecnologia":str(r.get("Tecnologia")).upper(),"Periodicidad":str(r.get("Periodicidad")).upper(),
                "Ubicaciones":ubic,"F. Inicio":str(fi)
            })
    return pro, err

def descargar_borrador(): return json.dumps({"cliente":st.session_state.cliente,"sedes":st.session_state.sedes,"usuarios":st.session_state.usuarios},default=str)
def cargar_borrador(f): 
    try: st.session_state.update(json.load(f)); st.toast("Cargado")
    except: st.error("Error archivo")

# --- UI DIALOGS ---
@st.dialog("Nueva Sede")
def dialog_sede(index=None, d=None):
    b = d if d else {k: v for k, v in st.session_state.cliente.items()}; 
    if not d: b["nombre"] = ""
    n = st.text_input("Nombre Sede", b.get("nombre","").upper())
    c1,c2 = st.columns(2); dir_ = c1.text_input("Dirección", b.get("direccion","").upper())
    ld = DEPARTAMENTOS + ["OTRO"]; vd = b.get("departamento", "").upper(); id_d = ld.index(vd) if vd in ld else 0
    dp = c2.selectbox("Depto", ld, index=id_d); lm = COLOMBIA_DATA.get(dp, []) + ["OTRO"] if dp != "OTRO" else []
    vm = b.get("municipio", "").upper(); id_m = lm.index(vm) if vm in lm else 0
    mn = st.selectbox("Muni", lm, index=id_m) if dp != "OTRO" else None
    df, mf = (st.text_input("Escriba Depto").upper() if dp == "OTRO" else dp), (st.text_input("Escriba Muni").upper() if (mn == "OTRO" or dp == "OTRO") else mn)
    c3,c4 = st.columns(2); r = c3.text_input("Resp", b.get("responsable", "").upper()); e = c4.text_input("Mail", b.get("email", "").lower()); t = st.text_input("Tel", b.get("telefono", ""))
    if st.button("Guardar Sede", type="primary"):
        if not n: st.error("Nombre obligatorio")
        else:
            ns = {"nombre": limpiar_texto(n), "direccion": dir_, "departamento": df, "municipio": mf, "responsable": r, "email": e, "telefono": t}
            if index is not None: st.session_state.sedes[index] = ns
            else: st.session_state.sedes.append(ns)
            st.rerun()

@st.dialog("Agregar Usuario")
def dialog_usuario():
    st.markdown("#### Datos"); c1,c2=st.columns(2); n=c1.text_input("Nombres").upper(); a=c2.text_input("Apellidos").upper()
    cd = st.columns([1.5, 2.5, 4]); td=cd[0].selectbox("Tipo", LISTAS["TIPO_DOC"]); dc=cd[1].text_input("Número"); em=cd[2].text_input("Email").lower()
    c3,c4=st.columns(2); fn=c3.date_input("Nacimiento", date(1990,1,1)); ge=c4.selectbox("Genero", LISTAS["GENERO"])
    st.markdown("#### Laboral"); c5,c6=st.columns([1,2]); nv=c5.selectbox("Nivel", LISTAS["NIVEL_EDUCATIVO"]); ti=c6.selectbox("Titulo", LISTAS["TITULO"])
    c7,c8=st.columns(2); oc=c7.selectbox("Ocupación", LISTAS["OCUPACION"]); ia = LISTAS["AREA"].index(st.session_state.last_area) if st.session_state.last_area in LISTAS["AREA"] else 0
    ar = c8.selectbox("Área", LISTAS["AREA"], index=ia); oa = st.text_input("Otra Área").upper() if ar == "OTRO" else ""
    st.divider(); sn = [s["nombre"] for s in st.session_state.sedes]; is_ = sn.index(st.session_state.last_sede) if st.session_state.last_sede in sn else 0
    se = st.selectbox("Sede", sn, index=is_) if sn else None
    c9,c10,c11=st.columns(3); co=c9.selectbox("Cob", LISTAS["COBERTURA"]); te=c10.selectbox("Tec", LISTAS["TECNOLOGIA"]); pe=c11.selectbox("Per", LISTAS["PERIODICIDAD"])
    ub=st.multiselect("Ubicaciones", LISTAS["UBICACION_CORPO"]); c_m, c_a = st.columns(2); mi = c_m.selectbox("Mes", LISTAS["MESES"]); ai = c_a.number_input("Año", 2024, 2030, date.today().year)
    if st.button("Guardar", type="primary", use_container_width=True):
        if not all([n,a,dc,em,ub,se]): st.error("Incompleto")
        elif ar == "OTRO" and not oa: st.error("Falta Otra Área")
        else:
            fi = get_primer_dia_mes(mi, ai); st.session_state.last_sede = se; st.session_state.last_area = ar
            for u in ub: st.session_state.usuarios.append({"Nombres":n,"Apellidos":a,"Tipo Doc":td,"Documento":dc,"Correo":em,"F. Nacimiento":str(fn),"Genero":ge,"Nivel":nv,"Titulo":ti,"Ocupacion":oc,"Area":ar,"Otra Area":oa,"Sede":se,"Cobertura":co,"Tecnologia":te,"Periodicidad":pe,"Ubicaciones":u,"F. Inicio":str(fi)})
            st.rerun()

# --- CONFIRMACIÓN ---
@st.dialog("Confirmación de Ingreso")
def dialog_confirmar_envio():
    st.markdown("#### ¿Está seguro de procesar este ingreso?")
    cli = st.session_state.cliente
    st.info(f"🏢 **Cliente:** {cli['razon_social']} | NIT: {cli['nit']}")
    c1,c2,c3 = st.columns(3); c1.metric("Sedes", len(st.session_state.sedes)); c2.metric("Usuarios", len({u['Documento'] for u in st.session_state.usuarios})); c3.metric("Registros", len(st.session_state.usuarios))
    if st.button("✅ SÍ, REGISTRAR Y NOTIFICAR", type="primary", use_container_width=True):
        with st.spinner("Guardando en BD y enviando correos..."):
            ok, msg = guardar_en_base_datos(st.session_state.cliente, st.session_state.sedes, st.session_state.usuarios)
        if ok and "error" not in msg.lower(): 
            st.session_state.envio_exitoso = True; st.rerun()
        elif ok: # Se guardó en BD pero falló el correo
            st.warning(f"⚠️ Datos guardados, pero alerta de correo: {msg}")
            st.session_state.envio_exitoso = True # Permitimos salir
        else: 
            st.error(f"Error fatal: {msg}")

# --- MAIN ---
c_l, c_t, c_o = st.columns([1, 2, 1])
if os.path.exists("logo.png"): c_l.image("logo.png", width=180)
c_t.markdown("<h2 style='text-align:center;color:#002060;'>Ingreso usuarios dosimetría - Sievert S.A.S</h2>", unsafe_allow_html=True)

cli_ok, sed_ok = verificar_estado_general(); usu_ok = len(st.session_state.usuarios) > 0
nm_cli = st.session_state.cliente["razon_social"] if st.session_state.cliente["razon_social"] else "PENDIENTE"
nm_short = (nm_cli[:15] + '..') if len(nm_cli) > 15 else nm_cli

c_t.markdown(f"""
    <div style='text-align:center;'>
        <span class='status-badge {'status-ok' if cli_ok else 'status-err'}'>CLI: {nm_short}</span>
        <span class='status-badge {'status-ok' if sed_ok else 'status-err'}'>SEDES: {len(st.session_state.sedes)}</span>
        <span class='status-badge {'status-ok' if usu_ok else 'status-err'}'>REG: {len(st.session_state.usuarios)}</span>
    </div>
""", unsafe_allow_html=True)

with c_o.popover("⚙️"):
    st.download_button("💾 JSON", descargar_borrador(), "data.json"); u = st.file_uploader("📂"); 
    if u and st.button("Restaurar"): cargar_borrador(u); st.rerun()

st.write("")
if 'envio_exitoso' in st.session_state: st.success("✅ ¡Datos guardados y notificados exitosamente!"); st.stop()

with st.expander("🏢 Cliente / Sedes", expanded=True):
    c1,c2,c3,c4=st.columns(4)
    st.session_state.cliente["razon_social"]=c1.text_input("Razón",st.session_state.cliente["razon_social"]).upper()
    st.session_state.cliente["nit"]=c2.text_input("NIT",st.session_state.cliente["nit"])
    st.session_state.cliente["email"]=c3.text_input("Email",st.session_state.cliente["email"]).lower()
    st.session_state.cliente["telefono"]=c4.text_input("Tel",st.session_state.cliente["telefono"])
    c5,c6,c7,c8=st.columns(4)
    st.session_state.cliente["responsable"]=c5.text_input("Resp",st.session_state.cliente["responsable"]).upper()
    st.session_state.cliente["cargo"]=c6.text_input("Cargo",st.session_state.cliente["cargo"]).upper()
    st.session_state.cliente["direccion"]=c7.text_input("Dir",st.session_state.cliente["direccion"]).upper()
    ld=DEPARTAMENTOS+["OTRO"]; vd=st.session_state.cliente["departamento"].upper(); id_d=ld.index(vd) if vd in ld else 0
    dp=c8.selectbox("Depto",ld,index=id_d,key="cd"); lm=COLOMBIA_DATA.get(dp,[])+["OTRO"] if dp!="OTRO" else []
    vm=st.session_state.cliente["municipio"].upper(); id_m=lm.index(vm) if vm in lm else 0
    cm,cf=st.columns([1,3]); mn=cm.selectbox("Muni",lm,index=id_m,key="cm") if dp!="OTRO" else None
    st.session_state.cliente["departamento"]=(st.text_input("TxtDepto",vd).upper() if dp=="OTRO" else dp)
    st.session_state.cliente["municipio"]=(st.text_input("TxtMuni",vm).upper() if (mn=="OTRO" or dp=="OTRO") else mn)
    
    st.markdown("---"); c_t, c_b = st.columns([6,1]); c_t.markdown("#### Sedes"); 
    if c_b.button("➕"): dialog_sede()
    if st.session_state.sedes:
        cs=st.columns(4)
        for i,s in enumerate(st.session_state.sedes):
            with cs[i%4].container():
                st.markdown(f"**{s['nombre']}**<br><small>{s['municipio']}</small>", unsafe_allow_html=True)
                if st.button("✎", key=f"e{i}", use_container_width=True): dialog_sede(i,s)

st.markdown("### 👥 Usuarios")
t1, t2 = st.tabs(["👤 Manual", "🚀 Masivo"])
with t1:
    b, g = st.columns([1,3]); 
    if b.button("➕ Usuario", type="primary", use_container_width=True): 
        if not st.session_state.sedes: st.error("Falta Sede")
        else: dialog_usuario()
    with g.expander("⚡ Generar Filas"):
        c1,c2,c3,c4=st.columns(4); nr=c1.number_input("#",1,50,5); sn=[s["nombre"] for s in st.session_state.sedes]; sg=c2.selectbox("Sede",sn) if sn else None; tg=c3.selectbox("Tec",LISTAS["TECNOLOGIA"]); pg=c4.selectbox("Per",LISTAS["PERIODICIDAD"])
        if st.button("Generar", use_container_width=True):
            if not sg: st.error("Falta Sede")
            else: st.session_state.usuarios.extend([{"Nombres":"","Apellidos":"","Tipo Doc":"CC","Documento":"","Correo":"","F. Nacimiento":str(date(1990,1,1)),"Genero":"OTRO","Nivel":"PROFESIONAL","Titulo":"OTRO","Ocupacion":"OTRO","Area":"RADIOLOGIA","Otra Area":"","Sede":sg,"Cobertura":"ARL","Tecnologia":tg,"Periodicidad":pg,"Ubicaciones":"TORAX","F. Inicio":str(date.today().replace(day=1))} for _ in range(nr)]); st.rerun()

with t2:
    c1, c2 = st.columns([1,2]); c1.download_button("📥 Plantilla", generar_plantilla_excel(), "Plantilla.xlsx", use_container_width=True)
    u = st.file_uploader("Excel", ["xlsx"], label_visibility="collapsed")
    if u and st.button("Procesar", type="primary", use_container_width=True):
        us, er = procesar_excel_masivo(u)
        # 🟢 CORRECCIÓN DEL ERROR VISUAL [...]
        if er:
            for e in er:
                if "Duplicado" in e: st.warning(e)
                else: st.error(e)
        if us: st.session_state.usuarios.extend(us); st.success(f"✅ {len(us)} Registros cargados.")

if st.session_state.usuarios:
    st.divider(); m1, m2 = st.columns(2); m1.metric("Registros", len(st.session_state.usuarios)); m2.metric("Sedes", len({u["Sede"] for u in st.session_state.usuarios}))
    sn = [s["nombre"] for s in st.session_state.sedes]
    df_ed = st.data_editor(st.session_state.usuarios, num_rows="dynamic", use_container_width=True, height=500, key="ed", column_config={
        "Sede": st.column_config.SelectboxColumn(options=sn, required=True), "Genero": st.column_config.SelectboxColumn(options=LISTAS["GENERO"]),
        "Tipo Doc": st.column_config.SelectboxColumn(options=LISTAS["TIPO_DOC"]), "Tecnologia": st.column_config.SelectboxColumn(options=LISTAS["TECNOLOGIA"]),
        "Periodicidad": st.column_config.SelectboxColumn(options=LISTAS["PERIODICIDAD"]), "Cobertura": st.column_config.SelectboxColumn(options=LISTAS["COBERTURA"]),
        "Area": st.column_config.SelectboxColumn(options=LISTAS["AREA"], required=True), "Otra Area": st.column_config.TextColumn(help="Si Área es OTRO"),
        "Ubicaciones": st.column_config.TextColumn(required=True), "Nombres": st.column_config.TextColumn(required=True),
        "Apellidos": st.column_config.TextColumn(required=True), "Documento": st.column_config.TextColumn(required=True), "Correo": st.column_config.TextColumn(required=True)
    })
    if len(df_ed) != len(st.session_state.usuarios) or df_ed != st.session_state.usuarios: st.session_state.usuarios = df_ed if isinstance(df_ed, list) else df_ed.to_dict('records')

st.markdown("<br>", unsafe_allow_html=True); c1,c2,c3=st.columns([1,2,1])
if c2.button("🚀 ENVIAR SOLICITUD DE INGRESO", type="primary", use_container_width=True):
    co, so = verificar_estado_general(); to, tm = validar_tabla_usuarios_estricta()
    if not (co and so): st.error("⚠️ Faltan datos Cliente/Sedes")
    elif not to: st.error(tm)
    else: dialog_confirmar_envio()

st.markdown("<div class='footer'>© 2025 Sievert S.A.S | v.34.0</div>", unsafe_allow_html=True)
