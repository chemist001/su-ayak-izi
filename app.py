import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import time
import datetime
import base64
import io
from google import genai
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"].strip())
from supabase import create_client, Client
# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
def raporu_kaydet(tesis_adi, mavi, yesil, gri, toplam, ai_analizi=""):
    try:
        # 1. Giriş kontrolü
        if 'user' not in st.session_state or st.session_state.user is None:
            st.error("Kayıt hatası: Lütfen önce sisteme giriş yapın!")
            return

        # 2. Supabase'e işlemden saniyeler önce kimliği (token) gösteriyoruz!
        if 'session' in st.session_state:
            supabase.auth.set_session(
                st.session_state.session.access_token, 
                st.session_state.session.refresh_token
            )

        user_id = st.session_state.user.id
        
# 3. .from_ kullanarak versiyon hatasını aşıyoruz ve FULL PAKETİ yolluyoruz
        
        # Tabloları veritabanı formatına (JSON) çevirme
        sorumlular_json = st.session_state.get('sorumlular_tablosu').to_dict(orient='records') if 'sorumlular_tablosu' in st.session_state and not st.session_state['sorumlular_tablosu'].empty else []
        sinir_json = st.session_state.get('sistem_siniri_tablosu').to_dict(orient='records') if 'sistem_siniri_tablosu' in st.session_state and not st.session_state['sistem_siniri_tablosu'].empty else []
        hedefler_json = st.session_state.get('hedef_tablosu').to_dict(orient='records') if 'hedef_tablosu' in st.session_state and not st.session_state['hedef_tablosu'].empty else []

        response = supabase.from_("tesis_raporlari").insert({
            "user_id": user_id,
            "tesis_adi": str(tesis_adi),
            "mavi_su": float(mavi),
            "yesil_su": float(yesil),
            "gri_su": float(gri),
            "toplam_su": float(toplam),
            "ai_analizi": str(ai_analizi),
            
            # --- İSİMLER TAMAMEN SENİN KODUNA GÖRE EŞLEŞTİRİLDİ ---
            "firma_adresi": st.session_state.get('adres', 'Belirtilmedi'),
            "sektor": st.session_state.get('sektor', 'Belirtilmedi'),
            "yetkili_kisi": st.session_state.get('yetkili', 'Belirtilmedi'),
            "iletisim_email": st.session_state.get('email', 'Belirtilmedi'),
            "iletisim_telefon": st.session_state.get('telefon', 'Belirtilmedi'),
            "sorumlular_tablosu": sorumlular_json,
            "sistem_siniri_tablosu": sinir_json,
            "hedefler_tablosu": hedefler_json
        }).execute()
        
        st.success("Raporunuz Kaydedildi")
        
    except Exception as e:
        st.error(f"Kayıt sırasında bir hata oluştu: {str(e)}")

def gecmis_raporlari_getir():
    try:
        # Oturum kontrolü
        if 'user' not in st.session_state or st.session_state.user is None:
            return None
            
        # Supabase'den sadece bu kullanıcının verilerini en yeniden eskiye doğru (desc) çekiyoruz
        response = supabase.from_("tesis_raporlari").select("*").order("olusturma_tarihi", desc=True).execute()
        return response.data
        
    except Exception as e:
        st.error(f"Geçmiş raporlar yüklenirken hata oluştu: {str(e)}")
        return None

supabase: Client = init_connection()
# --- KULLANICI GİRİŞ SİSTEMİ (AUTH) ---
if 'user' not in st.session_state:
    st.session_state.user = None

if 'mavi_su_sonuc' not in st.session_state:
    st.session_state.mavi_su_sonuc = 0.0
if 'yesil_su_sonuc' not in st.session_state:
    st.session_state.yesil_su_sonuc = 0.0
if 'gri_su_sonuc' not in st.session_state:
    st.session_state.gri_su_sonuc = 0.0

def login_user(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
        time.sleep(1)
    except Exception as e:
        # Eğer bir hata varsa, hatanın tam teknik adını ekrana basacak:
        st.error(f"Giriş hatası detayı: {str(e)}")
        return 
    
    # Bu komut kesinlikle except bloğunun DIŞINDA ve try ile aynı hizada olmalı:
    st.rerun()

def register_user(email, password):
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Kayıt başarılı! Lütfen Giriş Yap sekmesinden sisteme girin.")
    except Exception as e:
        st.error(f"Gerçek Hata: {str(e)}")

# Kullanıcı giriş yapmamışsa Giriş Ekranını göster ve UYGULAMAYI DURDUR
if st.session_state.user is None:
    st.title("💧 H2O Denge - Su Ayak İzi Platformu")
    st.markdown("Lütfen devam etmek için giriş yapın veya yeni bir tesis hesabı oluşturun.")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Yeni Kayıt"])
    
    with tab1:
        st.subheader("Sisteme Giriş")
        login_email = st.text_input("E-Posta", key="login_email")
        login_pass = st.text_input("Şifre", type="password", key="login_pass")
        if st.button("Giriş Yap", type="primary"):
            login_user(login_email, login_pass)
            
    with tab2:
        st.subheader("Yeni Tesis Kaydı")
        reg_email = st.text_input("E-Posta", key="reg_email")
        reg_pass = st.text_input("Şifre (En az 6 karakter)", type="password", key="reg_pass")
        if st.button("Kayıt Ol"):
            register_user(reg_email, reg_pass)

    def raporu_kaydet(tesis_adi, mavi, yesil, gri, toplam, ai_analizi=""):
        try:
            # 1. Oturumdaki kullanıcının güvenli ID'sini alıyoruz
            user_id = st.session_state.user.id
            
            # --- YENİ: Tabloları veritabanının anlayacağı formata (JSON) çeviriyoruz ---
            sorumlular_json = st.session_state.get('sorumlular_tablo').to_dict(orient='records') if 'sorumlular_tablo' in st.session_state and not st.session_state['sorumlular_tablo'].empty else []
            sinir_json = st.session_state.get('sistem_siniri_tablo').to_dict(orient='records') if 'sistem_siniri_tablo' in st.session_state and not st.session_state['sistem_siniri_tablo'].empty else []
            hedefler_json = st.session_state.get('hedefler_tablo').to_dict(orient='records') if 'hedefler_tablo' in st.session_state and not st.session_state['hedefler_tablo'].empty else []

            # 2. Supabase'deki 'tesis_raporlari' kasasına verileri FULL PAKET gönderiyoruz
            data, count = supabase.table("tesis_raporlari").insert({
                "user_id": user_id,
                "tesis_adi": tesis_adi,
                "mavi_su": float(mavi),
                "yesil_su": float(yesil),
                "gri_su": float(gri),
                "toplam_su": float(toplam),
                "ai_analizi": ai_analizi,
                
                # --- YENİ EKLENEN RAFLAR (Firma Bilgileri ve Tablolar) ---
                "firma_adresi": st.session_state.get('address', 'Belirtilmedi'),
                "sektor": st.session_state.get('sector', 'Belirtilmedi'),
                "yetkili_kisi": st.session_state.get('contact_person', 'Belirtilmedi'),
                "iletisim_email": st.session_state.get('email', 'Belirtilmedi'),
                "iletisim_telefon": st.session_state.get('c_phone', 'Belirtilmedi'),
                "sorumlular_tablosu": sorumlular_json,
                "sistem_siniri_tablosu": sinir_json,
                "hedefler_tablosu": hedefler_json
            }).execute()
            
            st.success("🎉 Harika! Raporunuz (ve tüm firma detayları) başarıyla Supabase veritabanına kaydedildi!")
        
        except Exception as e:
            st.error(f"Kayıt sırasında bir hata oluştu: {str(e)}")
    
    # Giriş yapılmadıysa uygulamanın (hesaplayıcının) geri kalanını okuma
    st.stop()

# --- GİRİŞ YAPILDIYSA BURADAN AŞAĞISI ÇALIŞIR ---
st.sidebar.success(f"Giriş yapıldı: {st.session_state.user.email}")
if st.sidebar.button("Çıkış Yap"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()
# ---------------------------
# --- TABLO ODAK SORUNUNU ÇÖZEN HAFIZA ---
if 'gri_su_tablo_editor' not in st.session_state:
    st.session_state['gri_su_tablo_editor'] = {"edited_rows": {}, "added_rows": [], "deleted_rows": []}
# Hesaplama butonunun kapanmasını engelleyen kilit
if 'hesaplama_tamam' not in st.session_state:
    st.session_state['hesaplama_tamam'] = False
# Sürdürülebilirlik Hedefleri Tablosu Hafızası
if 'hedef_tablosu' not in st.session_state:
    st.session_state['hedef_tablosu'] = pd.DataFrame([
        {"Hedef Yılı": "", "Hedef Açıklaması": ""}
    ])
# Su Yönetimi Sorumluları Tablosu Hafızası
if 'sorumlular_tablosu' not in st.session_state:
    st.session_state['sorumlular_tablosu'] = pd.DataFrame([
        {"Sorumlu Kişi": "", "Görev": "", "İletişim": ""},
        {"Sorumlu Kişi": "", "Görev": "", "İletişim": ""}
    ])   
    
# ==========================================
# 1. GÖRSEL TASARIM VE CSS
# ==========================================
def add_bg_from_url():
    st.html(
        """
        <style>
        /* 10 NUMARALI TASARIM: SIVI METALİK MAVİ (Fütüristik) */
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2560&auto=format&fit=crop");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }

        /* Kart Tasarımları (Fütüristik, parlak zeminde keskin duran beyaz paneller) */
        div[data-testid="stVerticalBlock"] > div {
            background-color: rgba(255, 255, 255, 0.93); /* Arka planın enerjisini hafif içeri alan şeffaflık */
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4); /* Derin ve vurgulu gölge */
            border: 1px solid rgba(255, 255, 255, 0.3); /* İnce teknolojik çerçeve */
        }
        
        /* Sidebar (Kenar Çubuğu - Yarı saydam teknolojik panel) */
        [data-testid="stSidebar"] {
            background-color: rgba(245, 247, 250, 0.85);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        /* Başlık Renkleri (Sıvı metal konseptiyle uyumlu karizmatik koyu lacivert/gri tonlar) */
        h1 { color: #0f172a !important; } 
        h2 { color: #1e293b !important; }
        h3 { color: #334155 !important; }

        /* Rapor Başlıkları */
        .report-header {
            background-color: rgba(241, 245, 249, 0.85);
            padding: 10px;
            border-radius: 6px;
            border-left: 5px solid #3b82f6; /* Parlak teknolojik mavi vurgu */
            margin-bottom: 10px;
            font-weight: bold;
            color: #0f172a;
        }
        </style>
        """
    )
# ==========================================
# 2. HESAPLAMA MOTORU (BACKEND)
# ==========================================
class WaterFootprintCalculator:
    
    def calculate_blue_water(self, v_in=0.0, v_discharge=0.0, same_basin=True, 
                            evaporation=0.0, incorporation=0.0, lost_return=0.0):
        """
        WFN Mavi Su Ayak İzi Hesaplaması
        Öncelik Kütle Denkliğindedir (Mass Balance). 
        """
     
        # 1. Yaklaşım: Kütle Denkliği (Giren ve çıkan su biliniyorsa)
        if v_in > 0 and v_discharge >= 0:
            if same_basin:
                # Aynı havzaya dönüyorsa, aradaki kayıp tüketimdir (Mavi Su)
                return max(0.0, v_in - v_discharge)
            else:
                # Farklı havzaya gidiyorsa, giren suyun tamamı kaybedilmiş (Mavi Su) sayılır
                return v_in
                
        # 2. Yaklaşım: Doğrudan WFN Temel Formülü (Eğer doğrudan sahadan bu veriler toplanabilmişse)
        return evaporation + incorporation + lost_return

    def calculate_green_water(self, evaporation=0.0, incorporation=0.0):
        """
        Yeşil Su Ayak İzi (Tesis içi açık alan yağmur suyu kullanımı)
        """
        return evaporation + incorporation

    def calculate_grey_water(self, pollutants):
        """
        Kritik Kirletici Algoritması:
        Tüm kirleticileri hesaplar ve en yüksek olanı seçer.
        """
        max_grey_water = 0.0
        critical_pollutant_name = "Kirlilik Yok / Veri Girilmedi"
        
        for p in pollutants:
            name = p.get("name", "Bilinmeyen Kirletici")
            load = p.get("load", 0.0)      
            c_max = p.get("c_max", 1.0)    
            c_nat = p.get("c_nat", 0.0)    
            
            # Güvenlik Kontrolü: Doğal kirlilik, yasal limitten büyük/eşitse atla
            if c_max <= c_nat or load == 0:
                continue 
                
            current_grey = load / (c_max - c_nat)
            
            if current_grey > max_grey_water:
                max_grey_water = current_grey
                critical_pollutant_name = name
                
        return {
            "value_m3": max_grey_water,
            "critical_pollutant": critical_pollutant_name
        }

# ==========================================
# 3. PDF RAPOR MOTORU (YENİ SİSTEM)
# ==========================================
class ISO14046Report(FPDF):
    def header(self):
        pass 

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

    def tr_chars(self, text):
        """Türkçe karakter düzeltici"""
        replacements = {
            'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I',
            'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
        }
        for tr, eng in replacements.items():
            text = text.replace(tr, eng)
        return text

    def create_cover_page(self, company_name, year):
        self.add_page()
        self.set_line_width(1)
        self.rect(10, 10, 190, 277) 
        
        self.set_font('Arial', 'B', 24)
        self.ln(60)
        self.cell(0, 10, self.tr_chars(company_name), 0, 1, 'C')
        
        self.set_font('Arial', 'B', 16)
        self.ln(20)
        self.cell(0, 10, f"{year} Yili ISO 14046:2014", 0, 1, 'C')
        self.cell(0, 10, self.tr_chars("KURUMSAL SU AYAK IZI RAPORU"), 0, 1, 'C')
        
        self.ln(50)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, "Raporu Hazirlayan: Sistem Tarafindan Otomatik Uretilmistir", 0, 1, 'C')
        self.cell(0, 10, "Standard: TS EN ISO 14046", 0, 1, 'C')

    def add_section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, self.tr_chars(title), 0, 1, 'L', 1)
        self.ln(5)

    def add_key_value(self, key, value):
        self.set_font('Arial', 'B', 10)
        self.cell(50, 6, self.tr_chars(key), 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, self.tr_chars(f": {value}"), 0, 1)

    def add_table_row(self, data, widths, header=False):
        self.set_font('Arial', 'B' if header else '', 9)
        if header: self.set_fill_color(200, 220, 255)
        
        max_h = 6
        for item, w in zip(data, widths):
            self.cell(w, max_h, self.tr_chars(str(item)), 1, 0, 'C', header)
        self.ln()

def generate_full_report(data):
    pdf = ISO14046Report()
    
    # 1. KAPAK
    pdf.create_cover_page(data['company_info']['name'], data['report_info']['year'])
    
    # 2. GİRİŞ
    pdf.add_page()
    pdf.add_section_title("1. GIRIS VE KURUMSAL BILGILER")
    ci = data['company_info']
    pdf.add_key_value("Firma Adi", ci['name'])
    pdf.add_key_value("Adres", ci['address'])
    pdf.add_key_value("Telefon", ci['phone'])
    pdf.add_key_value("E-Mail", ci['email'])
    pdf.add_key_value("Sorumlu Kisi", ci['responsible'])
    pdf.ln(5)
    
    # 3. MAVİ SU
    pdf.add_section_title("4.1 MAVI SU AYAK IZI HESAPLARI")
    
    # Mavi Su Tablosu
    cols = ["Bilesen", "Veri Kaynagi", "Miktar (m3)"]
    widths = [80, 60, 50]
    pdf.add_table_row(cols, widths, header=True)
    
    total_blue = 0
    for item in data['blue_water_sources']:
        row = [item['source'], item['data_source'], f"{item['amount']:.2f}"]
        pdf.add_table_row(row, widths)
        total_blue += item['amount']
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(140, 6, "TOPLAM", 1, 0, 'R')
    pdf.cell(50, 6, f"{total_blue:.2f}", 1, 1, 'C')
    pdf.ln(5)

    if data['charts']['blue']:
        pdf.image(data['charts']['blue'], x=50, w=100)
    pdf.ln(5)

    # 4. GRİ SU
    pdf.add_page()
    pdf.add_section_title("4.2 GRI SU AYAK IZI HESAPLARI")
    
    pdf.add_table_row(["Bilesen", "Yontem", "Miktar (m3)"], widths, header=True)
    total_grey = 0
    for item in data['grey_water_sources']:
        row = [item['source'], item['data_source'], f"{item['amount']:.2f}"]
        pdf.add_table_row(row, widths)
        total_grey += item['amount']
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(140, 6, "TOPLAM", 1, 0, 'R')
    pdf.cell(50, 6, f"{total_grey:.2f}", 1, 1, 'C')
    pdf.ln(5)

    if data['charts']['grey']:
        pdf.image(data['charts']['grey'], x=50, w=100)
    
    # 5. SONUÇ
    pdf.ln(10)
    pdf.add_section_title("5. SONUC VE DEGERLENDIRME")
    pdf.multi_cell(0, 5, pdf.tr_chars(f"2024 yili verilerine gore isletmenin toplam Mavi Su Ayak Izi {total_blue:.2f} m3/yil, Gri Su Ayak Izi ise {total_grey:.2f} m3/yil olarak hesaplanmistir."))
    pdf.ln(5)
    pdf.multi_cell(0, 5, pdf.tr_chars("Bu rapor, ISO 14046 standardi cercevesinde, Turkuaz Belge basvuruSurecleri icin temel teskil etmesi amaciyla hazirlanmistir."))

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. GRAFİK OLUŞTURUCU
# ==========================================
def create_pie_chart(data_dict, title):
    if not data_dict or sum(data_dict.values()) == 0:
        return None
    
    labels = list(data_dict.keys())
    sizes = list(data_dict.values())
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#4a90e2', '#50e3c2', '#f5a623'])
    ax.axis('equal')
    plt.title(title)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf

# ==========================================
# 5. SAYFA İÇERİKLERİ 
# ==========================================
def show_home_page():
    """Ana Sayfa - Su Ayak İzi Nedir?"""
    st.title("💧 Su Ayak İzi Nedir?")
    st.markdown("### Görünmeyen Suyun Hikayesi")
    
    st.write("""
    Su ayak izi, bir kişinin, ürünün veya sektörün birim zamanda harcadığı ve kirlettiği 
    toplam temiz su miktarını ifade eden bütüncül bir göstergedir. 
    Yalnızca musluktan akan suyu değil, yediğimiz gıdadan giydiğimiz kıyafete kadar 
    tüm üretim süreçlerindeki **'sanal su'** tüketimini de kapsar.
    """)
    
    st.info("💡 **Biliyor muydunuz?** Bir fincan kahvenin su ayak izi yaklaşık **140 litredir**. 1 kg sığır etinin su ayak izi ise **15.400 litre**.")
    
    st.info("""💡 Türkiye, kişi başına düşen yıllık yaklaşık 1.313 m³ kullanılabilir su miktarı ile "su stresi çeken" ülkeler statüsündedir. 2030 yılına kadar bu rakamın 1.000 m³'ün altına düşerek **su fakiri** kategorisine geçme riskimiz bulunmaktadır.""")
    
    st.markdown("### Su Ayak İzinin 3 Rengi")

# Senin 3'lü sütun yapın aynen kalıyor
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 1. Başlık Vurgusu (Sadece 'Mavi' kelimesi boyalı)
        st.markdown("""
        <h4><span style='background-color:#17a2b8; color:white; padding:4px 10px; border-radius:5px;'>Mavi</span> Su Ayak İzi</h4>
        """, unsafe_allow_html=True)
        
        st.write("Mavi su ayak izi, doğrudan su kaynaklarından (akarsular, göller, yer altı suyu) kullanılan su miktarını ifade eder. Bu, suyun bir ürüne, hizmete veya süreçlere dahil edilmesi sırasında yapılan su çekimini temsil eder.")
        st.markdown("- 🏭 Sanayi üretimi\n- 🚰 Evsel kullanım\n- 🌾 Tarımsal sulama")
        
        # 2. Renkli Formül Bandı (Kartın en altına yapışık gibi duracak)
        st.markdown("""
        <div style='background-color:#17a2b8; color:white; padding:10px; border-radius:5px; text-align:center; font-size:14px; margin-top:15px;'>
        Mavi Su Ayakizi = Buharlaşan Mavi Su + Ürüne Dahil Olan Mavi Su + Drenaj Miktarı
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <h4><span style='background-color:#28a745; color:white; padding:4px 10px; border-radius:5px;'>Yeşil</span> Su Ayak İzi</h4>
        """, unsafe_allow_html=True)
        
        st.write("Yeşil su ayak izi, bitkilerin büyümesi için kullanılan yağış suyunu ifade eder. Bu, toprak tarafından emilen ve bitkiler tarafından kullanılan su miktarını kapsar ve suyun doğal döngüsü içinde yer aldığı süreçleri değerlendirir.")
        st.markdown("- 🌲 Orman ürünleri\n- 🚜 Yağmurla beslenen tarım\n- 🌧️ Yağmur hasadı")
        
        st.markdown("""
        <div style='background-color:#28a745; color:white; padding:10px; border-radius:5px; text-align:center; font-size:14px; margin-top:15px;'>
        Yeşil Su Ayakizi = Buharlaşan Yeşil Su + Ürüne Dahil Olan Yeşil Su
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <h4><span style='background-color:#6c757d; color:white; padding:4px 10px; border-radius:5px;'>Gri</span> Su Ayak İzi</h4>
        """, unsafe_allow_html=True)
        
        st.write("Oluşan kirliliği, su kalitesi standartlarına (doğal konsantrasyona) seyreltmek için gereken teorik temiz su miktarıdır. Bu, bir ürün veya süreç nedeniyle kirlenen suyun doğrudan veya dolaylı olarak temizlenmesi gereken su miktarını hesaplar.")
        st.markdown("- 🧪 Kimyasal atıklar\n- 🚿 Atıksu deşarjı\n- 🏭 Termal kirlilik")
        
        st.markdown("""
        <div style='background-color:#6c757d; color:white; padding:10px; border-radius:5px; text-align:center; font-size:14px; margin-top:15px;'>
        Gri Su Ayakizi = Kirletici Yükü / (C<sub>max</sub> - C<sub>nat</sub>)
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")

    st.title("📜 Su Verimliliği Yönetmeliği ve Belgelendirme")
    
    st.info("""27 Aralık 2024 tarihli ve 32765 sayılı Resmi Gazete'de yayımlanan 
    **Su Verimliliği Yönetmeliği** kapsamında, endüstriyel tesisler için 3 seviyeli bir 
    belgelendirme sistemi getirilmiştir.
    """)

    st.markdown("### 🏆 Belgelendirme Seviyeleri ve Kriterler")
    
    tab_mavi, tab_yesil, tab_turkuaz = st.tabs([
        " Mavi Su Belgesi", 
        " Yeşil Su Belgesi", 
        " Turkuaz Su Belgesi"
    ])

    with tab_mavi:
        st.header("Mavi Su Verimliliği Belgesi")
        st.write("Su verimliliği yönetim sistemini kuran tesislere verilir.")
        st.markdown("""
        **Gerekli Kriterler**
        * ✅ Su verimliliği konusunda yeterli sayıda sorumlu personel görevlendirilmesi.
        * ✅ Mevcut su kullanım durumunun belirlenmesi (Su Envanteri).
        * ✅ Su verimliliği hedeflerinin belirlenmesi.
        * ✅ Eğitim faaliyetlerinin düzenlenmesi.
        * ✅ Verimli ekipmanların (musluk, duş başlığı vb.) kullanılması.
        * ✅ Bilgilendirici yazılı ve görsel materyallerin kullanılması.
        """)

    with tab_yesil:
        st.header("Yeşil Su Verimliliği Belgesi")
        st.write("Suyu verimli kullanan tesislere verilir.")
        st.markdown("""
        **Endüstriyel Tesisler İçin Kriterler**
        * ✅ **Alternatif Kaynaklar:** Toplam su kullanımının **%10'unun** geleneksel olmayan kaynaklardan sağlanması.
        * ✅ **Sektörel Rehberler:** NACE Koduna uygun tekniklerin uygulanması.
        * ✅ **Yönetim Sistemi:** *TS ISO 46001 Belgesine sahip olunması.
        """)
        st.warning("*Bu kriter ilk yeşil belge başvurusunda aranmayacak, yeşil belge yenileme başvurusunda zorunlu olacaktır.")

    with tab_turkuaz:
        st.header("Turkuaz Su Verimliliği Belgesi")
        st.write("Atık su geri kazanımı yapan tesislere verilir.")
        st.markdown("""
        **Endüstriyel Tesisler İçin Kriterler**
        * ✅ **Geri Kazanım:** Atık suyun en az **%20'sinin** geri kazanılarak yeniden kullanılması.
        * ✅ **Su Ayak İzi:** **TS EN ISO 14046 Su Ayak İzi** standardı kapsamında belgenin olması.
        * ✅ NACE koduna uygun su verimliliği rehber dokümanlarında yer alan tekniklerin uygulanması.
        * ✅ TSE tarafından verilen **TS ISO 46001** Su Verimliliği Yönetim Sistemi Belgesine sahip olması.
        """)


# --- ANA SAYFA ZENGİNLEŞTİRME BLOKLARI (KOPYALA - YAPIŞTIR) ---
        
    # 1. ÇARPICI İSTATİSTİK KARTLARI (Streamlit Metrikleri)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="1 Pamuklu Tişört", value="2.700 L", delta="Sanal Su", delta_color="off")
    with col2:
        st.metric(label="1 Kg Sığır Eti", value="15.400 L", delta="Tarımsal Yük", delta_color="inverse")
    with col3:
        st.metric(label="Sanayi Payı (TR)", value="%11", delta="Toplam Tüketim", delta_color="off")
    with col4:
        st.metric(label="Arıtılmayan Atıksu", value="%80+", delta="Küresel Deşarj", delta_color="inverse")


 # 2. GRAFİKLER (Şık ve Küçültülmüş Versiyon)
    
    grafik_col1, grafik_col2 = st.columns(2)

    with grafik_col1:
        st.markdown("<p style='text-align: center; font-size: 18px; color:#1b6f8a;'>Türkiye Su Tüketimi</p>", unsafe_allow_html=True)
        
        # Figsize daha da küçültüldü
        fig1, ax1 = plt.subplots(figsize=(2.5, 2.5))
        labels = ['Tarım', 'Sanayi', 'Evsel']
        sizes = [74, 11, 15]
        colors = ['#7dd3fc', '#bbf7d0', '#e2e8f0']
        
        # Yazı boyutları grafiğe uygun olarak (7) küçültüldü
        ax1.pie(
    sizes, 
    labels=labels, 
    colors=colors, 
    autopct='%1.1f%%', 
    startangle=90,
    labeldistance=1.1,   # label'ı dışarı alır
    pctdistance=0.8,     # yüzdeyi içerde ama merkeze yakın tutar
    wedgeprops=dict(width=0.4, edgecolor='w'),
    textprops={'fontsize': 7}
)
        ax1.axis('equal') 
        fig1.patch.set_alpha(0.0)
        
        # Ortadaki sütun oranını daralttık ki grafik ekrana yayılıp büyümesin
        sol, orta, sag = st.columns([1, 1.65, 1])
        with orta:
            st.pyplot(fig1, use_container_width=True) 

    with grafik_col2:
        st.markdown("<p style='text-align: center; font-size: 18px; color:#1b6f8a;'>Ürün Bazlı 'Gizli Su' Yükü (Litre)</p>", unsafe_allow_html=True)
        
        # Figsize bar grafik için kibar bir dikdörtgene (3.5, 2.5) ayarlandı
        fig2, ax2 = plt.subplots(figsize=(2.5, 1.5), dpi=200)
        urunler = ['Kahve', 'Peynir', 'Tişört', 'Sığır Eti']
        su_miktari = [140, 3180, 2700, 15400]
        
        # Çubuk kalınlıkları inceltildi (height=0.6)
        ax2.barh(urunler, su_miktari, color='#bae6fd', height=0.6)
        ax2.set_xlabel('Su Tüketimi (Litre)', fontsize=4)
        ax2.tick_params(axis='both', which='major', labelsize=4)
        
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        fig2.patch.set_alpha(0.0)
        
        # Kenar boşlukları artırılıp grafik alanı daraltıldı
        sol2, orta2, sag2 = st.columns([1, 3, 1]) 
        with orta2:
            st.pyplot(fig2, use_container_width=True)
            
            # (col3 bloğunun bittiği yerden sonra, girintiye (indentation) dikkat ederek ekleyin)
    
    st.markdown("---") # Araya ince bir çizgi çeker, tasarımı ayırır
    
    # Destek ve iletişim butonu
    st.info("💡 Hesaplamalar veya tesis verileriyle ilgili yardıma mı ihtiyacınız var?")
    st.link_button("🎧 Destek ve İletişim İçin Tıklayın", "https://www.sanayikampusu.com/iletisim")
    # --------------------------------------------------------------
import streamlit as st
import pandas as pd
import plotly.express as px

def show_calculator_page():
    # --- KALICI HAFIZA (SESSION STATE) REZERVASYONLARI ---
    # Firma Bilgileri
    if 'firma_adi' not in st.session_state: st.session_state['firma_adi'] = ""
    if 'sektor' not in st.session_state: st.session_state['sektor'] = ""
    if 'adres' not in st.session_state: st.session_state['adres'] = ""
    if 'yetkili' not in st.session_state: st.session_state['yetkili'] = ""
    if 'email' not in st.session_state: st.session_state['email'] = ""
    if 'telefon' not in st.session_state: st.session_state['telefon'] = ""
    if 'rapor_yili' not in st.session_state: st.session_state['rapor_yili'] = ""
    if 'rapor_tarihi' not in st.session_state: st.session_state['rapor_tarihi'] = None
        

    # Mavi Su
    if 'sebeke_suyu' not in st.session_state: st.session_state['sebeke_suyu'] = 0.0
    if 'kuyu_suyu' not in st.session_state: st.session_state['kuyu_suyu'] = 0.0
    if 'diger_su' not in st.session_state: st.session_state['diger_su'] = 0.0
    if 'desarj' not in st.session_state: st.session_state['desarj'] = 0.0
    if 'ayni_havza' not in st.session_state: st.session_state['ayni_havza'] = True
    if 'kuru_proses' not in st.session_state: st.session_state['kuru_proses'] = False

    # Yeşil Su
    if 'yesil_evap' not in st.session_state: st.session_state['yesil_evap'] = 0.0
    if 'yesil_incorp' not in st.session_state: st.session_state['yesil_incorp'] = 0.0

    # Gri Su (Dinamik Tablo)
    if 'gri_tablo' not in st.session_state:
        st.session_state['gri_tablo'] = pd.DataFrame([
            {"Parametre": "KOİ", "Yük (kg/yıl)": 0.0, "C_max Limit (kg/m³)": 0.1, "C_nat Doğal (kg/m³)": 0.0},
            {"Parametre": "BOİ", "Yük (kg/yıl)": 0.0, "C_max Limit (kg/m³)": 0.05, "C_nat Doğal (kg/m³)": 0.0}
        ])
    # -----------------------------------------------------
    st.set_page_config(page_title="Su Ayak İzi Hesaplama", layout="wide")
    st.title("💧 Hesaplama Aracı")
    st.caption("ISO 14046 ve WFN Metodolojisine Uygun Gate-to-Gate Analizi")

    # Sekmeli Yapı (Senin tasarımın)
    tab_firma, tab_mavi, tab_yesil, tab_gri, = st.tabs([
        "🏢 Firma Profili", "🟦 Mavi Su", "🟩 Yeşil Su", "⬛ Gri Su",
    ])

 # --- 1. FIRMA PROFILI ---
    with tab_firma:
        st.header("Firma Bilgileri")
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Firma Ünvanı", value=st.session_state.get('firma_adi', ''))
            st.session_state['firma_adi'] = company_name
            
            sector = st.text_input("Firma Sektörü", value=st.session_state.get('sektor', ''))
            st.session_state['sektor'] = sector
            
            address = st.text_input("Firma Adresi", value=st.session_state.get('adres', ''))
            st.session_state['adres'] = address

            # YENİ VE ŞIK: Raporlama Yılı (Açılır Menü / Selectbox)
            yillar = ["2024", "2025", "2026", "2027", "2028", "2029", "2030"]
            varsayilan_yil = st.session_state.get('rapor_yili', "2026") # Hafızada yoksa 2026 seçili gelsin
            
            # Eğer hafızadaki yıl bizim listemizde varsa onu bul, yoksa 2026'nın sırasını (2) seç
            secili_index = yillar.index(varsayilan_yil) if varsayilan_yil in yillar else 2
            
            rapor_yili = st.selectbox("Raporlama Yılı", options=yillar, index=secili_index)
            st.session_state['rapor_yili'] = rapor_yili

        with col2:
            contact_person = st.text_input("Yetkili Kişi Adı Soyadı", value=st.session_state.get('yetkili', ''))
            st.session_state['yetkili'] = contact_person
            
            email = st.text_input("Yetkili E-posta", value=st.session_state.get('email', ''))
            st.session_state['email'] = email
            
            c_phone = st.text_input("Telefon", value=st.session_state.get('telefon', ''))
            st.session_state['telefon'] = c_phone

            # Rapor Tarihi (Takvim Formatında)
            rapor_tarihi = st.date_input("Rapor Tarihi", value=st.session_state.get('rapor_tarihi', None))
            st.session_state['rapor_tarihi'] = rapor_tarihi
            
            # Kolonların altına Sorumlular Tablosunu ekliyoruz
        st.divider()
        st.subheader("👥 Su Yönetimi Sorumluları")
        st.write("Raporda yer alacak 'Sorumlu Kişilerin İletişim Bilgileri' tablosunu buradan düzenleyebilirsiniz. Yeni satır eklemek için tablonun altına tıklayın.")
        
          # 739. satırdan itibaren silip şunu yapıştır:

        # 1. Aşama: Veriyi hafızadan çek (eğer yoksa boş bir tablo yarat)
        if 'sorumlu_kisiler_tablosu' not in st.session_state:
            st.session_state['sorumlu_kisiler_tablosu'] = pd.DataFrame(
                columns=["Sorumlu Kişi", "Görev", "İletişim"]
            )
        
        # 2. Aşama: Editörü kullanarak geçici bir tablo oluştur
        gecici_sorumlu_df = st.data_editor(
            st.session_state['sorumlu_kisiler_tablosu'],
            column_config={
                "Sorumlu Kişi": st.column_config.TextColumn("Sorumlu Kişi", required=True),
                "Görev": st.column_config.TextColumn("Görev"),
                "İletişim": st.column_config.TextColumn("İletişim")
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
        
        # 3. Aşama: "Kaydet" butonu
        if st.button("Kaydet"):
            st.session_state['sorumlu_kisiler_tablosu'] = gecici_sorumlu_df
            st.success("Sorumlu bilgileri başarıyla güncellendi!")
            st.rerun()

    # --- 2. MAVİ SU (Kütle Denkliği ile Düzeltilmiş Yapı) ---
    with tab_mavi:
        st.header("Mavi Su Verileri (Kütle Denkliği)")
        st.info("Lütfen tesise giren toplam suyu ve tesisten çıkan atıksu deşarj miktarını giriniz.")
        
        st.subheader("1. Tesise Giren Su (Su Çekimi)")
        c1, c2, c3 = st.columns(3)
        sebeke_suyu = c1.number_input("Şebeke Suyu (m³/yıl)", min_value=0.0, value=st.session_state['sebeke_suyu'])
        st.session_state['sebeke_suyu'] = sebeke_suyu
        
        kuyu_suyu = c2.number_input("Kuyu Suyu (m³/yıl)", min_value=0.0, value=st.session_state['kuyu_suyu'])
        st.session_state['kuyu_suyu'] = kuyu_suyu
        
        diger_su = c3.number_input("Taşıma/Kaynak Suyu (m³/yıl)", min_value=0.0, value=st.session_state['diger_su'])
        st.session_state['diger_su'] = diger_su
        
        toplam_giren = sebeke_suyu + kuyu_suyu + diger_su
        st.write(f"**Toplam Giren Su ($V_{{in}}$):** {toplam_giren} m³/yıl")
        
        st.divider()
        st.subheader("2. Tesisten Çıkan Su (Deşarj)")
        c4, c5 = st.columns(2)
        desarj_miktari = c4.number_input("Toplam Atıksu Deşarjı (m³/yıl)", min_value=0.0, value=st.session_state['desarj'])
        st.session_state['desarj'] = desarj_miktari
        
        ayni_havza_mi = c5.checkbox("Deşarj edilen su, çekildiği havzaya/nehre mi dönüyor?", value=st.session_state['ayni_havza'])
        st.session_state['ayni_havza'] = ayni_havza_mi
        
        # --- BURADAN İTİBAREN YENİ EKLENECEK KISIM ---
        st.divider()
        if st.button("💧 Mavi Su Ayak İzini Hesapla"):
            hesaplanan_mavi = 0.0
            
            # Hesaplama Mantığı (ISO 14046 ve Su Ayak İzi Ağı metodolojisi)
            if ayni_havza_mi:
                # Aynı havzaya dönüyorsa: Çekilen - Deşarj Edilen
                # Eksi değer çıkmaması için max(0, ...) kullanıyoruz
                hesaplanan_mavi = max(0.0, toplam_giren - desarj_miktari) 
            else:
                # Başka havzaya deşarj ediliyorsa çekilen suyun tamamı Mavi Su tüketimi sayılır
                hesaplanan_mavi = toplam_giren
            
            # --- DÜZELTİLEN KISIM: AŞAĞIDAKİ İKİ SATIRI İÇERİ (SAĞA) ALDIK ---
            
            # 1. Çıkan sonucu ANA HAFIZAYA atıyoruz (Sadece butona basılınca çalışır)
            st.session_state.mavi_su_sonuc = hesaplanan_mavi
                
            # 2. Kullanıcıya ekranda gösteriyoruz
            st.success(f"✅ Mavi Su Ayak İzi Başarıyla Hesaplandı: {hesaplanan_mavi:.2f} m³/yıl")

    # --- 3. YEŞİL SU ---
    with tab_yesil:
        st.header("Yeşil Su Verileri")
        c1, c2 = st.columns(2)
        green_evap = c1.number_input("Yağmur Suyu (m³/yıl)", min_value=0.0, value=st.session_state['yesil_evap'])
        st.session_state['yesil_evap'] = green_evap
        
        green_incorp = c2.number_input("Ürüne Giren Yeşil Su (m³/yıl)", min_value=0.0, value=st.session_state['yesil_incorp'])
        st.session_state['yesil_incorp'] = green_incorp
        # --- YEŞİL SU HESAPLAMA BUTONU ---
        st.divider()
        if st.button("🌱 Yeşil Su Ayak İzini Hesapla"):
            # Formül: Yağmur Suyu Evaporasyonu + Ürüne Giren Su
            hesaplanan_yesil = green_evap + green_incorp
            
            # 1. Çıkan sonucu ANA HAFIZAYA atıyoruz (Kaydet butonu için)
            st.session_state.yesil_su_sonuc = hesaplanan_yesil
            
            # 2. Kullanıcıya ekranda gösteriyoruz
            st.success(f"✅ Yeşil Su Ayak İzi Başarıyla Hesaplandı: {hesaplanan_yesil:.2f} m³/yıl")

    # --- 4. GRİ SU ---
    with tab_gri:
        st.header("Gri Su Verileri (Kritik Kirletici)")
        st.write("Laboratuvar analizlerinizdeki kirlilik parametrelerini aşağıya ekleyiniz.")
        
        # 1. Editör (Kalıcı hafızayı gösterir)
        duzenlenmis_df = st.data_editor(
            st.session_state['gri_tablo'], 
            num_rows="dynamic", 
            use_container_width=True,
            key="gri_editor_key" 
        )
        
        st.divider()
    
        # 2. Butona basılınca çalışacak "Mühürleme ve Hesaplama" bloğu
        if st.button("⚙️ Gri Su Ayak İzini Hesapla"):
            # ÖNEMLİ: Tablodaki en son veriyi anında hafızaya alıyoruz
            st.session_state['gri_tablo'] = duzenlenmis_df 
            
            # Eğer tablo boşsa veya veriler None ise uyarı ver
            if duzenlenmis_df.empty or duzenlenmis_df.isnull().values.any():
                st.warning("Lütfen tabloda boş hücre bırakmayın ve verileri tam girin.")
            else:
                try:
                    pollutants_list = []
                    # Burada 'Parametre' gibi isimlerin tablonla tam eşleştiğinden emin ol!
                    for index, row in duzenlenmis_df.iterrows():
                        pollutants_list.append({
                            "name": str(row["Parametre"]),
                            "load": float(row["Yük (kg/yıl)"]),
                            "c_max": float(row["C_max Limit (kg/m³)"]),
                            "c_nat": float(row["C_nat Doğal (kg/m³)"])
                        })
                    
                    # Hesaplama motorunu çalıştır
                    calc = WaterFootprintCalculator()
                    res_grey_dict = calc.calculate_grey_water(pollutants_list)
                    
                    # Sonuçları hafızaya yaz
                    st.session_state.gri_su_sonuc = res_grey_dict["value_m3"]
                    st.session_state.kritik_kirletici_isim = res_grey_dict["critical_pollutant"]
                    
                    st.success(f"✅ Hesaplandı! Kritik Kirletici: **{st.session_state.kritik_kirletici_isim}** | Hacim: **{st.session_state.gri_su_sonuc:,.2f} m³/yıl**")
                    
                except Exception as e:
                    st.error(f"Hesaplama hatası (Veri tiplerini kontrol edin): {str(e)}")
            
def sayfa_veri_kalitesi():
    st.header("Veri Kalitesi ve Sistem Sınırı")
    
    # 1. Aşama: Veriyi hafızadan çek
    if 'sistem_siniri_tablosu' not in st.session_state:
        st.session_state['sistem_siniri_tablosu'] = pd.DataFrame(
            columns=["Bileşen", "Kaynak", "Veri Kaynağı", "Veri Doğrulama"]
        )

    # 2. Aşama: Editör (Bu editör direkt session_state'i değiştirmiyor, geçici bir değişken döndürüyor)
    gecici_df = st.data_editor(
        st.session_state['sistem_siniri_tablosu'],
        column_config={
            # ... (Senin column_config ayarların aynen kalacak) ...
            "Bileşen": st.column_config.SelectboxColumn("Bileşen", options=["Mavi Su", "Gri Su", "Yeşil Su"], required=True),
            "Kaynak": st.column_config.SelectboxColumn("Kaynak", options=["Şebeke", "Kuyu", "Diğer", "Endüstriyel Atıksu"], required=True),
            "Veri Kaynağı": st.column_config.SelectboxColumn("Veri Kaynağı", options=["Sayaç ve Fatura", "Analiz Raporları", "Sayaç", "Tahmin/Beyan"], required=True),
            "Veri Doğrulama": st.column_config.SelectboxColumn("Veri Doğrulama", options=["Tüketim Kayıtları", "Fatura Kontrolü", "Laboratuvar Beyanı", "İç Kayıtlar"], required=True)
        },
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True 
    )

    # 3. Aşama: "Kaydet" butonu ile hafızaya mühürle
    if st.button("Kaydet"):
        st.session_state['sistem_siniri_tablosu'] = gecici_df
        st.success("Veriler başarıyla kaydedildi!")
        st.rerun() # Sayfayı yenileyerek kaydın kesinleşmesini sağla

    # --- 6. RAPORLAMA ---
def sayfa_raporlama():
    st.header("Sonuç ve PDF Çıktısı")
        
    # Sadece kilidi açmak için butonu kullanıyoruz
    company_name = st.session_state.get('firma_adi', '')
    
    # 1. Mavi Su Yeşil Su ve Gri Su Girdilerini Çek ve Toplamı Bul
    sebeke = st.session_state.get('sebeke_suyu', 0.0)
    kuyu = st.session_state.get('kuyu_suyu', 0.0)
    diger = st.session_state.get('diger_su', 0.0)
    toplam_giren = sebeke + kuyu + diger
    desarj_miktari = st.session_state.get('desarj', 0.0)
    ayni_havza_mi = st.session_state.get('ayni_havza', False)
    green_evap = st.session_state.get('yesil_evap', 0.0)
    green_incorp = st.session_state.get('yesil_incorp', 0.0)
    # --- GRİ SU GİRDİLERİ (Kirlilik Tablosu) ---
    duzenlenmis_df = st.session_state.get('gri_tablo')
    pollutants_list = []
    # Metin verilerini senin 'Firma Profili'nde belirlediğin Türkçe isimlerden çekiyoruz
    address = st.session_state.get('adres', 'Belirtilmedi')
    sector = st.session_state.get('sektor', 'Belirtilmedi')
    contact_person = st.session_state.get('yetkili', 'Belirtilmedi')
    email = st.session_state.get('email', 'Belirtilmedi')
    c_phone = st.session_state.get('telefon', 'Belirtilmedi')
    
    # Rapor tarihi ve yılı
    rapor_yili = st.session_state.get('rapor_yili', '2026')
    rapor_tarihi = st.session_state.get('rapor_tarihi', None)

    # PDF'in içine basılacak olan tabloları çekiyoruz (Boşsalar çökmesin diye yedekli)
    duzenlenmis_sorumlular = st.session_state.get('sorumlular_tablosu', pd.DataFrame(columns=["Sorumlu Kişi", "Görev", "İletişim"]))
    sistem_siniri_tablosu = st.session_state.get('sistem_siniri_tablosu', pd.DataFrame(columns=["Bileşen", "Kaynak", "Veri Kaynağı", "Veri Doğrulama"]))
    duzenlenmis_hedefler = st.session_state.get('hedef_tablosu', pd.DataFrame(columns=["Hedef Yılı", "Hedef Açıklaması"]))
    
    # Tablo boş değilse, içindeki verileri hesaplama motoru için listeye çeviriyoruz
    if duzenlenmis_df is not None and not duzenlenmis_df.empty:
        for index, row in duzenlenmis_df.iterrows():
            pollutants_list.append({
                "name": row["Parametre"],
                "load": float(row["Yük (kg/yıl)"]),
                "c_max": float(row["C_max Limit (kg/m³)"]),
                "c_nat": float(row["C_nat Doğal (kg/m³)"])
            })
    
    # 2. Hesaplanan Ayak İzi Sonuçlarını Çek
    mavi = st.session_state.get('mavi_su_sonuc', 0.0)
    yesil = st.session_state.get('yesil_su_sonuc', 0.0)
    gri = st.session_state.get('gri_su_sonuc', 0.0)
    toplam = mavi + yesil + gri
    if st.button("HESAPLA VE RAPORU OLUŞTUR", type="primary"):
        if not company_name:
            st.error("Lütfen Firma Adını giriniz (Firma Profili sekmesinden).")
        else:
            st.session_state['hesaplama_tamam'] = True # Kilidi açtık

        # Kilit açıksa (veya açılmışsa) tüm sonuçları ve tabloyu göster
    if st.session_state.get('hesaplama_tamam', False):
            
        # Motoru Başlat (Buradan itibaren kodların eski haliyle tamamen aynı devam edecek)
            calc = WaterFootprintCalculator()
                
            # 1. Mavi Su Hesapla
            res_blue = calc.calculate_blue_water(
                v_in=toplam_giren, 
                v_discharge=desarj_miktari, 
                same_basin=ayni_havza_mi,
            )
                
            # 2. Yeşil Su Hesapla
            res_green = calc.calculate_green_water(green_evap, green_incorp)
                
            # 3. Gri Su Hesapla (Tablodaki verileri sözlüğe çevirerek gönder)
            pollutants_list = []
            for index, row in duzenlenmis_df.iterrows():
                pollutants_list.append({
                    "name": row["Parametre"],
                    "load": row["Yük (kg/yıl)"],
                    "c_max": row["C_max Limit (kg/m³)"],
                    "c_nat": row["C_nat Doğal (kg/m³)"]
                })
                
            res_grey_dict = calc.calculate_grey_water(pollutants_list)
            res_grey = res_grey_dict["value_m3"]
                
            # Toplam
            total_wf = res_blue + res_green + res_grey
                
            # --- 1. EKRANA YAZDIRMA VE GRAFİK ---
            st.success(f"Hesaplama Tamamlandı: {company_name}")
            st.markdown("### Su Ayak İzi Sonuçları")
                
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("🟦 Mavi Su Ayak İzi", f"{res_blue:,.2f} m³/yıl")
            col_res2.metric("🟩 Yeşil Su Ayak İzi", f"{res_green:,.2f} m³/yıl")
            col_res3.metric("⬛ Gri Su Ayak İzi", f"{res_grey:,.2f} m³/yıl", delta=f"Kritik: {res_grey_dict['critical_pollutant']}", delta_color="off")
                
            st.info(f"**Toplam Tesis Su Ayak İzi:** {total_wf:,.2f} m³/yıl")


        # --- YENİ YERİ: HESAPLAMALARIN EN ALTINA ---
            st.markdown("---")
            st.subheader("🤖 AI Danışman Analizi")
                
            kullanici_sorusu = st.text_area("Tesis verilerinizle ilgili AI Danışmana ne sormak istersiniz?", height=100)
                
            if st.button("Danışmana Sor", type="primary"):
                if kullanici_sorusu:
                    with st.spinner("AI Danışman tesis verilerinizi analiz ediyor..."):
                            
                        # Verileri buraya "gizli zarf" gibi ekliyoruz
                        tesis_verileri = f"""
                        Tesisin Güncel Su Ayak İzi Verileri:
                        - Mavi Su: {res_blue:.2f} m3/yıl
                        - Yeşil Su: {res_green:.2f} m3/yıl
                        - Gri Su: {res_grey:.2f} m3/yıl
                        - Toplam: {total_wf:.2f} m3/yıl
                        """
                            
                        sistem_talimati = "Sen kıdemli bir sürdürülebilirlik denetçisisin. Yukarıdaki tesis verilerini analiz et. Vereceğin yanıta 'Merhaba, ben kıdemli yapay zeka asistanınız olarak paylaştığınız verileri derinlemesine analiz ettim.' cümlesi ile başla "
                        tam_soru = f"{sistem_talimati}\n\n{tesis_verileri}\n\nKullanıcı Sorusu: {kullanici_sorusu}"
                        
                        # --- İŞTE BURAYA GÜVENLİK AĞINI (TRY-EXCEPT) EKLİYORUZ ---
                        try:
                            response = client.models.generate_content(
                                model='gemini-flash-latest', # Senin orijinal ve çalışan model ismine geri döndük!
                                contents=tam_soru
                            )
                                
                            st.success("Analiz Tamamlandı!")
                            st.markdown(response.text)
                            
                        except Exception as e:
                            # Sunucu hatası (503 vb.) verirse kırmızı ekran çıkmaz, bu tatlı uyarı çıkar
                            st.warning("⏳ Yapay zeka sunucularında anlık bir yoğunluk yaşanıyor (High Demand). Lütfen 1-2 dakika sonra tekrar deneyin.")
                            st.info(f"Teknik Detay: {str(e)}")
                            
                else:
                    st.warning("Lütfen bir soru girin.")
                
            # Plotly Pasta Grafik
            st.markdown("### 📊 Su Ayak İzi Dağılımı")
            import plotly.express as px
            chart_data = pd.DataFrame({
                "Bileşen": ["Mavi Su", "Yeşil Su", "Gri Su"],
                "Hacim (m³/yıl)": [res_blue, res_green, res_grey]
            })
            fig = px.pie(chart_data, values="Hacim (m³/yıl)", names="Bileşen", color="Bileşen",
                         color_discrete_map={"Mavi Su": "#3498db", "Yeşil Su": "#2ecc71", "Gri Su": "#95a5a6"}, hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- YENİ EKLENEN: SÜRDÜRÜLEBİLİRLİK HEDEFLERİ ---
            st.markdown("### 🎯 Sürdürülebilirlik Hedefleri")
            st.info("Raporunuzu oluşturmadan önce, tesisinizin su ayak izini azaltmaya yönelik aksiyon hedeflerinizi aşağıya ekleyebilirsiniz. Yeni hedef eklemek için tablonun en alt satırına tıklayın.")
            
            duzenlenmis_hedefler = st.data_editor(
                st.session_state['hedef_tablosu'], 
                num_rows="dynamic", 
                use_container_width=True,
                key="hedefler_tablo_editor" # Odak kaybını engelleyen kilit!
            )
            st.markdown("---")
            st.subheader("📄 Raporu PDF Olarak İndir")
            st.write("Yukarıdaki hesaplamalarınızı ve tablolarınızı içeren detaylı PDF raporunu hemen indirebilirsiniz.")
        
            def format_num_anlik(value):
                return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
            try:
                import datetime
                import os
                
                logo_firma = "logos/firma_logo.png" 
                logo_adaso = "logos/adaso_logo.png"
                
                class ProfessionalPDF_Anlik(FPDF):
                    def header(self):
                        if self.page_no() > 1:
                            self.set_line_width(1)
                            self.set_draw_color(0, 150, 136)
                            self.line(10, 8, 200, 8)
                            try: self.image(logo_firma, x=15, y=10, w=25)
                            except: pass
                            try: self.image(logo_adaso, x=165, y=10, w=25)
                            except: pass
                        self.ln(20)
        
                    def footer(self):
                        self.set_y(-20)
                        self.set_font("helvetica", style='', size=8) 
                        self.cell(100, 10, txt="Su Ayak Izi Raporu", ln=False, align='L')
                        self.cell(90, 10, txt=f"Sayfa {self.page_no()}/{{nb}}", ln=False, align='R')
    
                pdf = ProfessionalPDF_Anlik()
                pdf.alias_nb_pages()
    
                font_regular = "fonts/arial.ttf"
                font_bold = "fonts/arialbd.ttf"
                
                if os.path.exists(font_regular) and os.path.exists(font_bold):
                    pdf.add_font("ArialTR", style="", fname=font_regular, uni=True)
                    pdf.add_font("ArialTR", style="B", fname=font_bold, uni=True)
                    f_isim = "ArialTR"
                else:
                    f_isim = "helvetica"
    
                # --- KAPAK SAYFASI ---
                pdf.add_page()
                pdf.set_font(f_isim, size=24, style='B')
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.cell(190, 20, txt="SU AYAK IZI RAPORU", ln=True, align='C', fill=True)
                
                pdf.set_text_color(0, 0, 0) 
                pdf.ln(10)
                pdf.set_font(f_isim, size=14, style='B')
                current_year = datetime.datetime.now().year - 1
                pdf.cell(190, 10, txt=f"{current_year} Donemi", ln=True, align='C')
                
                pdf.ln(20)
                try: pdf.image(logo_firma, x=60, y=80, w=90) 
                except: pass
                
                pdf.set_y(220)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.set_text_color(0, 150, 136)
                pdf.cell(190, 10, txt="Adana Sanayi Odasi (ADASO)", ln=True, align='C')
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt=f"Bu Raporun Altyapisi Adana Sanayi Odasi Tarafindan Saglanmistir. Bu Rapor, {str(company_name)} Tarafindan MaviRota Platformu Kullanilarak Hazirlanmistir.", align='C')
    
                # --- İÇİNDEKİLER ---
                pdf.add_page()
                pdf.set_font(f_isim, size=16, style='B')
                pdf.cell(190, 10, txt="ICINDEKILER", ln=True, align='C')
                pdf.ln(10)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1. GIRIS", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.1. Kurulus Bilgileri", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.2. Tanimlar", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.3. Kurulus Su Yonetimi ve Sorumlular", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.4. Amac ve Kapsam", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.5. Hedef Kullanici", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.6. ISO 14046:2014 Uygunluk Aciklamasi", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="2. GENEL", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="2.1. Raporun Sahibi Olan Kurulus ve Raporlama Donemi", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="2.2. Operasyonel Sinirlar", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="3. METODOLOJI", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="3.1. Veri Kalitesi", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="3.2. Kabuller", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4. HESAPLAMALAR", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="4.1. Mavi Su Ayak Izi Hesaplamalari", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="4.2. Yesil Su Ayak Izi Hesaplamalari", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="4.3. Gri Su Ayak Izi Hesaplamalari", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="5. SONUC", ln=True)
                pdf.cell(190, 8, txt="6. SURDURULEBILIRLIK HEDEFLERI", ln=True)
                
                # --- BÖLÜM 1 ---
                pdf.add_page()
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="1. GIRIS", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.1. Kurulus Bilgileri", ln=True)
                pdf.set_font(f_isim, size=10, style='')
    
                rapor_yili = st.session_state.get('rapor_yili', '2026')
                rapor_tarihi_str = datetime.datetime.now().strftime("%d.%m.%Y")
                
                pdf.set_fill_color(240, 240, 240) 
                pdf.cell(60, 8, txt="Kurulus Adi", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(company_name)}", border=1, ln=True)
                pdf.cell(60, 8, txt="Tesis Adresi", border=1, fill=True)
                adres_text = str(address).replace("\n", " ")[:80] + ("..." if len(str(address)) > 80 else "")
                pdf.cell(130, 8, txt=adres_text, border=1, ln=True)
                pdf.cell(60, 8, txt="Tesis Sektoru", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(sector)}", border=1, ln=True)
                pdf.cell(60, 8, txt="Iletisim (Tel / E-Mail)", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(c_phone)} / {str(email)}", border=1, ln=True)
                pdf.cell(60, 8, txt="Rapordan Sorumlu Kisi", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(contact_person)}", border=1, ln=True)
                pdf.cell(60, 8, txt="Raporlama Yili", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{rapor_yili}", border=1, ln=True)
                pdf.cell(60, 8, txt="Rapor Tarihi", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{rapor_tarihi_str}", border=1, ln=True)
    
                pdf.ln(8)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.2. Tanimlar", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Mavi Su Ayak Izi: Dogrudan su kaynaklarindan (akarsular, goller, yer alti suyu) kullanilan su miktarini ifade eder. Suyun bir urune, hizmete veya sureclere dahil edilmesi sirasinda yapilan su cekimini temsil eder.\n\nYesil Su Ayak Izi: Bir tesisin faaliyetleri kapsaminda dogrudan veya dolayli olarak kullanilan hammaddelerin uretimi sirasinda tuketilen, yagis kaynakli suyun toplamini ifade eder..\n\nGri Su Ayak Izi: Kirliligi ifade eder ve mevcut cevre su kalitesi standartlarina dayanarak kirletici yukunu asimile etmek icin gereken tatli su hacmi olarak tanimlanir.")
    
                pdf.ln(8)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.3. Kurulus Su Yonetimi ve Sorumlular", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"{str(company_name)} olarak raporlama yilinda Mavi su olarak; insani kullanim ve uretim amaciyla sebeke, kuyu ogre diger tatli su kaynaklari temin edilmektedir. Mavi su ayak izi hesabinda sayac tuketimleri ve faturalar kabul edilerek hesap yapilmaktadir.\n\nGri su olarak; uretim amaciyla proseste kullanilan suyun endustriyel nitelikli atiksu faaliyeti sonucunda aritma tesislerine veya kanalizasyona desarji baz alinmaktadir.")
                
                pdf.ln(5)
                pdf.set_font(f_isim, size=11, style='B')
                pdf.cell(190, 8, txt="Tablo 1: Sorumlu Kisilerin Iletisim Bilgileri", ln=True)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(0, 0, 128)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(60, 8, txt="Sorumlu Kisi", border=1, fill=True, align='C')
                pdf.cell(80, 8, txt="Gorev", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="Iletisim", border=1, ln=True, fill=True, align='C')
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(f_isim, size=10, style='')
                
                try:
                    gecerli_sorumlular = [row for index, row in duzenlenmis_sorumlular.iterrows() if str(row["Görev"]).strip() != ""]
                    for row in gecerli_sorumlular:
                        sorumlu = str(row["Sorumlu Kişi"])[:30] 
                        gorev = str(row["Görev"])[:45]
                        iletisim = str(row["İletişim"])[:25]
                        pdf.cell(60, 8, txt=sorumlu, border=1, align='C')
                        pdf.cell(80, 8, txt=gorev, border=1, align='C')
                        pdf.cell(50, 8, txt=iletisim, border=1, ln=True, align='C')
                except:
                    pass
                    
                # --- BÖLÜM 1 DEVAMI VE BÖLÜM 2 ---
                pdf.add_page()
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.4. Amac ve Kapsam", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"{str(company_name)} bunyesinde su kullanimi ve su guvenligini saglamak icin olusturulan hedeflere ulasmak amaciyla kurulus bazinda bu rapor hazirlanmistir.\nRaporun amaci; {current_year} yili su kullanimi ve desarjina dair hesaplamalardan elde edilen miktarlarin dogrulanmasi ve seffaf bir surec olusturulmasidir.")
                
                pdf.ln(4)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.5. Hedef Kullanici", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Su ayak izi raporu hedef kullanicilari; Firmamiz Ust Yonetimi, Calisanlar, Tedarikciler ve Diger Paydaslardir.\nRapor, resmi kurumlarin talebi durumunda, surdurulebilirlik raporlarina veri talebi durumunda ve kuresel organizasyonlarin talebi durumunda ilgili kitlelere iletilir.")
    
                pdf.ln(4)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.6. Raporun ISO 14046:2014'e Uygunluguna Dair Aciklama", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Su Ayakizi Raporu 'ISO 14046:2014 Water Footprint - Principles, Requirements and Guidelines' gereklerine uygun olarak yazilimimiz tarafindan otomatik hazirlanmistir.")
    
                pdf.ln(6)
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="2. GENEL", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)
    
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="2.1. Raporun Sahibi Olan Kurulus ve Raporlama Donemi", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"Raporun sahibi {str(company_name)} olup, rapor 01 Ocak {current_year} - 31 Aralik {current_year} tarih araligi icin hazirlanmistir.")
    
                pdf.ln(4)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="2.2. Operasyonel Sinirlar", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"Raporun Kurulus bilgilerinde belirtilmis olan adresimizdeki tum operasyonlar sistem sinirlarina dahil edilmistir. {str(company_name)} faaliyetlerinden kaynaklanan su kullanim ve su desarjinin %100'u hesaplamalara dahil edilmistir.\nBu calismada kapidan kapiya (Gate-to-Gate) yaklasimi uygulanmistir.")
    
                # --- BÖLÜM 3 ---
                pdf.add_page()
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="3. METODOLOJI", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="3.1. Veri Kalitesi", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Hesaplamalarda kullanilan sebeke ve kuyu suyu verisi sayac tuketim kayitlarindan, diger tatli sular ise faturalardan alinmis oldugundan veri kalitesi yuksektir.")
                pdf.ln(3)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="3.2. Kabuller", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Gri Su Ayak izi hesaplarinda, uretim sonucu olusan atiksulari hesaplarken laboratuvar analiz sonuclarina gore en yuksek hacmi talep eden 'Kritik Kirletici' baz alinarak birincil veri kullanilmistir.")
    
                pdf.ln(4)
                pdf.set_font(f_isim, size=11, style='B')
                pdf.cell(190, 8, txt="Tablo 2: Genel Akis - Sistem Siniri", ln=True)
                
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(255, 192, 0) 
                pdf.cell(40, 8, txt="Bilesen", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="Kaynak", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="Veri Kaynagi", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="Veri Dogrulama", border=1, ln=True, fill=True, align='C')
                
                pdf.set_font(f_isim, size=10, style='')
    
                try:
                    for index, row in sistem_siniri_tablosu.iterrows():
                        bilesen = str(row["Bileşen"]) if pd.notna(row["Bileşen"]) else "-"
                        kaynak = str(row["Kaynak"]) if pd.notna(row["Kaynak"]) else "-"
                        veri_kaynagi = str(row["Veri Kaynağı"]) if pd.notna(row["Veri Kaynağı"]) else "-"
                        veri_dogrulama = str(row["Veri Doğrulama"]) if pd.notna(row["Veri Doğrulama"]) else "-"
                        
                        if bilesen != "-" or kaynak != "-":
                            pdf.cell(40, 8, txt=bilesen, border=1, align='C')
                            pdf.cell(50, 8, txt=kaynak, border=1, align='C')
                            pdf.cell(50, 8, txt=veri_kaynagi, border=1, align='C')
                            pdf.cell(50, 8, txt=veri_dogrulama, border=1, ln=True, align='C')
                except:
                    pass
    
                # --- BÖLÜM 4 ---
                pdf.ln(6)
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="4. HESAPLAMALAR", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)
    
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4.1. Mavi Su Ayak Izi Hesaplamalari", ln=True)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt="Tesisin dogrudan tukettigi, buharlastirdigi veya urune kattigi tatli su miktarini temsil eder. Tesis giris suyu ile desarj arasindaki kutle denkligine gore hesaplanmistir.")
                
                pdf.ln(3)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(95, 8, txt="Veri Kaynagi", border=1, fill=True, align='C')
                pdf.cell(95, 8, txt="Toplam Tuketim (m³/yil)", border=1, ln=True, fill=True, align='C')
                pdf.set_font(f_isim, size=10, style='')
                pdf.cell(95, 8, txt="Tesis Mavi Su Ayak Izi Hacmi", border=1, align='C')
                pdf.cell(95, 8, txt=f"{format_num_anlik(res_blue)}", border=1, ln=True, align='C')
    
                pdf.ln(5)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4.2. Yesil Su Ayak Izi Hesaplamalari", ln=True)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt="Tesis sinirlari icerisinde tuketilen veya urune katilan yagmur suyunu temsil eder.")
                
                pdf.ln(3)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(95, 8, txt="Veri Kaynagi", border=1, fill=True, align='C')
                pdf.cell(95, 8, txt="Toplam Tuketim (m³/yil)", border=1, ln=True, fill=True, align='C')
                pdf.set_font(f_isim, size=10, style='')
                pdf.cell(95, 8, txt="Tesis Yesil Su Ayak Izi Hacmi", border=1, align='C')
                pdf.cell(95, 8, txt=f"{format_num_anlik(res_green)}", border=1, ln=True, align='C')
    
                pdf.ln(5)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4.3. Gri Su Ayak Izi Hesaplamalari", ln=True)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt="Tesisten cikan atiksudaki kirlilik yukunun, dogal alici ortam standartlarina kadar seyreltilmesi icin gereken teorik tatli su miktarini temsil eder. En kritik kirletici parametresi baz alinmistir.")
                
                pdf.ln(3)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(95, 8, txt="Bilesen / Kritik Kirletici", border=1, fill=True, align='C')
                pdf.cell(95, 8, txt="Gereken Seyreltme Hacmi (m³/yil)", border=1, ln=True, fill=True, align='C')
                pdf.set_font(f_isim, size=10, style='')
                pdf.cell(95, 8, txt="Endustriyel Atiksu (Kritik Kirletici)", border=1, align='C')
                pdf.cell(95, 8, txt=f"{format_num_anlik(res_grey)}", border=1, ln=True, align='C')
    
                # --- BÖLÜM 5 ---
                pdf.add_page()
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="5. SONUC", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)
    
                total_vol = res_blue + res_green + res_grey
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt=f"Toplam Tesis Su Ayak Izi: {format_num_anlik(total_vol)} m³/yil", ln=True)
                pdf.ln(3)
    
                pdf.set_fill_color(0, 0, 128)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(70, 8, txt="Bilesen", border=1, align='C', fill=True)
                pdf.cell(70, 8, txt="Hacim (m³/yil)", border=1, align='C', fill=True)
                pdf.cell(50, 8, txt="Dagilim (%)", border=1, ln=True, align='C', fill=True)
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(f_isim, size=11, style='')
                p_blue = (res_blue / total_vol) * 100 if total_vol > 0 else 0
                p_green = (res_green / total_vol) * 100 if total_vol > 0 else 0
                p_grey = (res_grey / total_vol) * 100 if total_vol > 0 else 0
                
                pdf.cell(70, 8, txt="Mavi Su", border=1, align='C')
                pdf.cell(70, 8, txt=f"{format_num_anlik(res_blue)}", border=1, align='C')
                pdf.cell(50, 8, txt=f"% {p_blue:,.1f}", border=1, ln=True, align='C')
                
                pdf.cell(70, 8, txt="Yesil Su", border=1, align='C')
                pdf.cell(70, 8, txt=f"{format_num_anlik(res_green)}", border=1, align='C')
                pdf.cell(50, 8, txt=f"% {p_green:,.1f}", border=1, ln=True, align='C')
                
                pdf.cell(70, 8, txt="Gri Su", border=1, align='C')
                pdf.cell(70, 8, txt=f"{format_num_anlik(res_grey)}", border=1, align='C')
                pdf.cell(50, 8, txt=f"% {p_grey:,.1f}", border=1, ln=True, align='C')
                
                pdf.set_font(f_isim, size=11, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(70, 8, txt="TOPLAM", border=1, align='C', fill=True)
                pdf.cell(70, 8, txt=f"{format_num_anlik(total_vol)}", border=1, align='C', fill=True)
                pdf.cell(50, 8, txt="% 100", border=1, ln=True, align='C', fill=True)
    
                pdf.ln(6)
    
                etiketler = ['Mavi Su', 'Yesil Su', 'Gri Su'] 
                degerler = [res_blue, res_green, res_grey] 
                renkler = ['#678B99', '#8A9A70', '#C25946']
                
                if sum(degerler) > 0:
                    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
                    wedges, texts, autotexts = ax.pie(degerler, labels=etiketler, autopct='%1.1f%%', 
                                                     shadow=False, 
                                                     startangle=90, 
                                                     colors=renkler, 
                                                     textprops={'fontsize': 10, 'weight': 'bold'}, 
                                                     pctdistance=0.85, 
                                                     wedgeprops=dict(width=0.3, edgecolor='w')) 
                    
                    ax.axis('equal') 
                    ax.set_title("Toplam Tesis Su Ayak Izi Bilesimi", fontsize=12, fontweight='bold', pad=20)
                    
                    total = sum(degerler)
                    ax.text(0, 0, f"TOPLAM:\n{total:,.0f} m³", ha='center', va='center', fontsize=12, fontweight='bold')
        
                    grafik_yolu = "temp_grafik_anlik.png"
                    plt.savefig(grafik_yolu, format='png', dpi=300, bbox_inches='tight') 
                    plt.close(fig)
                    
                    pdf.image(grafik_yolu, x=35, y=pdf.get_y(), w=140) 
                    pdf.ln(100)
                    
                try:
                    gecerli_hedefler = [row for index, row in duzenlenmis_hedefler.iterrows() if str(row["Hedef Açıklaması"]).strip() != ""]
                    if len(gecerli_hedefler) > 0:
                        pdf.ln(6)
                        pdf.set_fill_color(0, 150, 136) 
                        pdf.set_text_color(255, 255, 255) 
                        pdf.set_font(f_isim, size=14, style='B')
                        pdf.cell(190, 10, txt="6. SURDURULEBILIRLIK HEDEFLERI", ln=True, align='L', fill=True)
                        pdf.set_text_color(0, 0, 0)
                        pdf.ln(5)
                        
                        pdf.set_font(f_isim, size=11, style='')
                        for i, hedef in enumerate(gecerli_hedefler):
                            hedef_metni = f"• {hedef['Hedef Yılı']} Yili Hedefi: {hedef['Hedef Açıklaması']}"
                            pdf.multi_cell(190, 6, txt=hedef_metni)
                except:
                    pass
    
                gecici_dosya_adi = f"anlik_rapor_{str(company_name)}.pdf"
                pdf.output(gecici_dosya_adi)
                
                with open(gecici_dosya_adi, "rb") as pdf_dosyasi:
                    pdf_bytes = pdf_dosyasi.read()
                    
                st.download_button(
                    label="Raporu PDF Olarak İndir",
                    data=pdf_bytes,
                    file_name=f"Su_Ayak_Izi_Raporu_{str(company_name)}.pdf",
                    mime="application/pdf",
                    key="btn_indir_anlik_sonuc"
                )
                
                if os.path.exists(gecici_dosya_adi): os.remove(gecici_dosya_adi)
                if os.path.exists("temp_grafik_anlik.png"): os.remove("temp_grafik_anlik.png")
    
            except Exception as e:
                st.error(f"Profesyonel PDF Oluşturma Hatası: {str(e)}")
            st.markdown("---")
            st.subheader("Raporu Veritabanına Kaydet")
            st.info("Hesaplamalarınızı ve tesis verilerinizi güvenli bulut sistemine kaydetmek için aşağıdaki butonu kullanın.")
            
            # Kullanıcıya rapor ismini değiştirebilme imkanı sunuyoruz
            kayit_adi = st.text_input("Rapor Başlığı (Veritabanında bu isimle görünecek):", value=f"{company_name} - 2026 Raporu")
            
            # Kaydet butonu (Diğer butonlarla karışmasın diye özel key atadık)
            if st.button("Raporu Kaydet", type="primary", key="btn_bulut_kayit_son"):
                # En tepeye yazdığımız fonksiyonu çağırıp motorun sonuçlarını içine atıyoruz
                raporu_kaydet(
                    tesis_adi=kayit_adi,
                    mavi=res_blue,
                    yesil=res_green,
                    gri=res_grey,
                    toplam=total_wf,
                    ai_analizi="AI Analizi ve Sürdürülebilirlik Hedefleri sisteme girildi." 
                )
            # ------------------------------------------------
    
   # --- 7. GEÇMİŞ RAPORLAR SEKME İÇERİĞİ ---
def sayfa_gecmis_raporlar():
    st.header("🗄️ Geçmiş Raporlarım")
    
    if st.button("🔄 Tabloyu Yenile", key="btn_yenile_gecmis"):
        st.rerun()
        
    veriler = gecmis_raporlari_getir()
    
    if veriler and len(veriler) > 0:
        df_gecmis = pd.DataFrame(veriler)
        
        # Görüntüleme için tabloyu hazırlıyoruz
        df_gosterim = df_gecmis[["tesis_adi", "mavi_su", "yesil_su", "gri_su", "toplam_su", "olusturma_tarihi"]].copy()
        df_gosterim.columns = ["Rapor Adı", "Mavi Su (m³)", "Yeşil Su (m³)", "Gri Su (m³)", "Toplam Su (m³)", "Kayıt Tarihi"]
        df_gosterim["Kayıt Tarihi"] = pd.to_datetime(df_gosterim["Kayıt Tarihi"]).dt.strftime("%d-%m-%Y %H:%M")
        
        # Ana tabloyu ekrana basıyoruz
        st.dataframe(df_gosterim, use_container_width=True, hide_index=True)
        
        rapor_secenekleri = [f"{row['tesis_adi']} ({row['olusturma_tarihi'][:10]})" for index, row in df_gecmis.iterrows()]
        secilen_rapor_etiketi = st.selectbox("İndirmek istediğiniz raporu seçin:", options=["Lütfen Seçiniz..."] + rapor_secenekleri)
        
        if secilen_rapor_etiketi != "Lütfen Seçiniz...":
            secilen_isim = secilen_rapor_etiketi.rsplit(" (", 1)[0]
            secilen_veri = df_gecmis[df_gecmis["tesis_adi"] == secilen_isim].iloc[0]

            # ==========================================
            # KRİTİK VERİ EŞLEŞTİRME (Supabase'den gelen geçmiş verileri PDF motoruna bağlıyoruz)
            # ==========================================
            company_name = secilen_veri['tesis_adi']
            res_blue = float(secilen_veri['mavi_su'])
            res_green = float(secilen_veri['yesil_su'])
            res_grey = float(secilen_veri['gri_su'])
            total_wf = float(secilen_veri['toplam_su'])

            # ==========================================
            # YENİ SİSTEM: VERİLERİ HAFIZADAN DEĞİL, DOĞRUDAN SUPABASE'DEN ÇEKİYORUZ
            # ==========================================
            def guvenli_metin(kolon_adi):
                # Eğer eski rapor olduğu için bu sütunlar henüz yoksa çökmeyi önler
                if kolon_adi in secilen_veri and pd.notna(secilen_veri[kolon_adi]) and secilen_veri[kolon_adi] != "":
                    return str(secilen_veri[kolon_adi])
                return "Belirtilmedi"

            address = guvenli_metin('firma_adresi')
            sector = guvenli_metin('sektor')
            contact_person = guvenli_metin('yetkili_kisi')
            email = guvenli_metin('iletisim_email')
            c_phone = guvenli_metin('iletisim_telefon')

            # JSON (Liste) formatında gelen tabloları PDF'in okuyabileceği formata çeviriyoruz
            # Eski raporlarda bu tablolar boş geleceği için hata vermesin diye yedek şablonlar ekledik
            sorumlular_db = secilen_veri.get('sorumlular_tablosu')
            if isinstance(sorumlular_db, list) and len(sorumlular_db) > 0:
                duzenlenmis_sorumlular = pd.DataFrame(sorumlular_db)
            else:
                duzenlenmis_sorumlular = pd.DataFrame(columns=["Sorumlu Kişi", "Görev", "İletişim"])

            sinir_db = secilen_veri.get('sistem_siniri_tablosu')
            if isinstance(sinir_db, list) and len(sinir_db) > 0:
                sistem_siniri_tablosu = pd.DataFrame(sinir_db)
            else:
                sistem_siniri_tablosu = pd.DataFrame(columns=["Bileşen", "Kaynak", "Veri Kaynağı", "Veri Doğrulama"])

            hedefler_db = secilen_veri.get('hedefler_tablosu')
            if isinstance(hedefler_db, list) and len(hedefler_db) > 0:
                duzenlenmis_hedefler = pd.DataFrame(hedefler_db)
            else:
                duzenlenmis_hedefler = pd.DataFrame(columns=["Hedef Yılı", "Hedef Açıklaması"])

            # ==========================================
            # --- 2. PROFESYONEL PDF İNDİRME MOTORU ---
            # ==========================================
                
            def format_num(value):
                    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            try:
            
                import datetime
                import os
                    
                logo_firma = "logos/firma_logo.png" 
                logo_adaso = "logos/adaso_logo.png"
                    
                class ProfessionalPDF(FPDF):
                    def header(self):
                        # Sayfa numarası 1'den büyükse (yani kapak değilse) logoları ve çizgiyi ekle
                        if self.page_no() > 1:
                            self.set_line_width(1)
                            self.set_draw_color(0, 150, 136)
                            self.line(10, 8, 200, 8)
                            try: self.image(logo_firma, x=15, y=10, w=25)
                            except: pass
                            try: self.image(logo_adaso, x=165, y=10, w=25)
                            except: pass
                            
                        # Kapak dahil her sayfada üstten boşluk bırak ki metinler yukarı yapışmasın
                        self.ln(20)

                    def footer(self):
                        self.set_y(-20)
                        self.set_font("helvetica", style='', size=8) 
                        self.cell(100, 10, txt="Su Ayak Izi Raporu", ln=False, align='L')
                        self.cell(90, 10, txt=f"Sayfa {self.page_no()}/{{nb}}", ln=False, align='R')

                pdf = ProfessionalPDF()
                pdf.alias_nb_pages()

                # ---------------------------------------------------------
                # KRİTİK NOKTA: TÜRKÇE FONTU SİSTEME 'uni=True' İLE GÖMME
                # ---------------------------------------------------------
                font_regular = "fonts/arial.ttf"
                font_bold = "fonts/arialbd.ttf"
                
                if os.path.exists(font_regular) and os.path.exists(font_bold):
                    # uni=True parametresi Türkçe karakterlerin silinmesini %100 engeller!
                    pdf.add_font("ArialTR", style="", fname=font_regular, uni=True)
                    pdf.add_font("ArialTR", style="B", fname=font_bold, uni=True)
                    f_isim = "ArialTR"
                else:
                    st.error("DİKKAT: C:\\Windows\\Fonts\\arial.ttf bulunamadı!")
                    f_isim = "helvetica" # Hata almamak için acil durum yedeği
                # ---------------------------------------------------------

                # --- KAPAK SAYFASI ---
                pdf.add_page()
                pdf.set_font(f_isim, size=24, style='B')
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.cell(190, 20, txt="SU AYAK İZİ RAPORU", ln=True, align='C', fill=True)
                
                pdf.set_text_color(0, 0, 0) 
                pdf.ln(10)
                pdf.set_font(f_isim, size=14, style='B')
                current_year = datetime.datetime.now().year - 1
                pdf.cell(190, 10, txt=f"{current_year} Dönemi", ln=True, align='C')
                
                pdf.ln(20)
                try: pdf.image(logo_firma, x=60, y=80, w=90) 
                except: pass
                
                pdf.set_y(220)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.set_text_color(0, 150, 136)
                pdf.cell(190, 10, txt="Adana Sanayi Odası (ADASO)", ln=True, align='C')
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt=f"Bu Raporun Altyapısı Adana Sanayi Odası Tarafından Sağlanmıştır. Bu Rapor, {str(company_name)} Tarafından MaviRota Platformu Kullanılarak Hazırlanmıştır.", align='C')

                # ==========================================
                # --- BÖLÜM 1: GİRİŞ VE KAPSAM ---
                # ==========================================
                # ==========================================
                # --- İÇİNDEKİLER SAYFASI ---
                # ==========================================
                pdf.add_page()
                pdf.set_font(f_isim, size=16, style='B')
                pdf.cell(190, 10, txt="İÇİNDEKİLER", ln=True, align='C')
                pdf.ln(10)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1. GİRİŞ", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.1. Kuruluş Bilgileri", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.2. Tanımlar", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.3. Kuruluş Su Yönetimi ve Sorumlular", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.4. Amaç ve Kapsam", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.5. Hedef Kullanıcı", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="1.6. ISO 14046:2014 Uygunluk Açıklaması", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="2. GENEL", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="2.1. Raporun Sahibi Olan Kuruluş ve Raporlama Dönemi", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="2.2. Operasyonel Sınırlar", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="3. METODOLOJİ", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="3.1. Veri Kalitesi", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="3.2. Kabuller", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4. HESAPLAMALAR", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="4.1. Mavi Su Ayak İzi Hesaplamaları", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="4.2. Yeşil Su Ayak İzi Hesaplamaları", ln=True)
                pdf.cell(10, 6, txt=""); pdf.cell(180, 6, txt="4.3. Gri Su Ayak İzi Hesaplamaları", ln=True)
                pdf.ln(4)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="5. SONUÇ", ln=True)
                pdf.cell(190, 8, txt="6. SÜRDÜRÜLEBİLİRLİK HEDEFLERİ", ln=True)
                
                # ==========================================
                # --- BÖLÜM 1: GİRİŞ ---
                # ==========================================
                pdf.add_page()
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="1. GİRİŞ", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.1. Kuruluş Bilgileri", ln=True)
                pdf.set_font(f_isim, size=10, style='')

                rapor_yili = st.session_state.get('rapor_yili', '2026')
                rapor_tarihi = st.session_state.get('rapor_tarihi', None)

                if rapor_tarihi:
                    rapor_tarihi_str = rapor_tarihi.strftime("%d.%m.%Y")
                else:
                    rapor_tarihi_str = "Belirtilmedi"
                
                # Detaylı Kuruluş Tablosu
                pdf.set_fill_color(240, 240, 240) 
                pdf.cell(60, 8, txt="Kuruluş Adı", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(company_name)}", border=1, ln=True)
                pdf.cell(60, 8, txt="Tesis Adresi", border=1, fill=True)
                adres_text = str(address).replace("\n", " ")[:80] + ("..." if len(str(address)) > 80 else "")
                pdf.cell(130, 8, txt=adres_text, border=1, ln=True)
                pdf.cell(60, 8, txt="Tesis Sektörü", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(sector)}", border=1, ln=True)
                pdf.cell(60, 8, txt="İletişim (Tel / E-Mail)", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(c_phone)} / {str(email)}", border=1, ln=True)
                pdf.cell(60, 8, txt="Rapordan Sorumlu Kişi", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{str(contact_person)}", border=1, ln=True)
                pdf.cell(60, 8, txt="Raporlama Yili", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{rapor_yili}", border=1, ln=True)
                pdf.cell(60, 8, txt="Rapor Tarihi", border=1, fill=True)
                pdf.cell(130, 8, txt=f"{rapor_tarihi_str}", border=1, ln=True)

                pdf.ln(8)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.2. Tanımlar", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Mavi Su Ayak İzi: Doğrudan su kaynaklarından (akarsular, göller, yer altı suyu) kullanılan su miktarını ifade eder. Suyun bir ürüne, hizmete veya süreçlere dahil edilmesi sırasında yapılan su çekimini temsil eder.\n\nYeşil Su Ayak İzi: Bir tesisin faaliyetleri kapsamında doğrudan veya dolaylı olarak kullanılan hammaddelerin üretimi sırasında tüketilen, yağış kaynaklı suyun toplamını ifade eder..\n\nGri Su Ayak İzi: Kirliliği ifade eder ve mevcut çevre su kalitesi standartlarına dayanarak kirletici yükünü asimile etmek için gereken tatlı su hacmi olarak tanımlanır.")

                pdf.ln(8)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.3. Kuruluş Su Yönetimi ve Sorumlular", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"{str(company_name)} olarak raporlama yılında Mavi su olarak; insani kullanım ve üretim amacıyla şebeke, kuyu ve diğer tatlı su kaynakları temin edilmektedir. Mavi su ayak izi hesabında sayaç tüketimleri ve faturalar kabul edilerek hesap yapılmaktadır.\n\nGri su olarak; üretim amacıyla proseste kullanılan suyun endüstriyel nitelikli atıksu faaliyeti sonucunda arıtma tesislerine veya kanalizasyona deşarjı baz alınmaktadır.")
                
                pdf.ln(5)
                pdf.set_font(f_isim, size=11, style='B')
                pdf.cell(190, 8, txt="Tablo 1: Sorumlu Kişilerin İletişim Bilgileri", ln=True)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(0, 0, 128)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(60, 8, txt="Sorumlu Kişi", border=1, fill=True, align='C')
                pdf.cell(80, 8, txt="Görev", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="İletişim", border=1, ln=True, fill=True, align='C')
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(f_isim, size=10, style='')
                # Arayüzden gelen tablo verilerini PDF'e yazdıran dinamik döngü
                gecerli_sorumlular = [row for index, row in duzenlenmis_sorumlular.iterrows() if str(row["Görev"]).strip() != ""]
                
                for row in gecerli_sorumlular:
                    # Tabloya sığması için metinleri biraz tıraşlıyoruz (taşıp PDF'i bozmaması için)
                    sorumlu = str(row["Sorumlu Kişi"])[:30] 
                    gorev = str(row["Görev"])[:45]
                    iletisim = str(row["İletişim"])[:25]
                    
                    pdf.cell(60, 8, txt=sorumlu, border=1, align='C')
                    pdf.cell(80, 8, txt=gorev, border=1, align='C')
                    pdf.cell(50, 8, txt=iletisim, border=1, ln=True, align='C')
                    
                # ==========================================
                # --- BÖLÜM 1 DEVAMI VE BÖLÜM 2 ---
                # ==========================================
                pdf.add_page()
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.4. Amaç ve Kapsam", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"{str(company_name)} bünyesinde su kullanımı ve su güvenliğini sağlamak için oluşturulan hedeflere ulaşmak amacıyla kuruluş bazında bu rapor hazırlanmıştır.\nRaporun amacı; {current_year} yılı su kullanımı ve deşarjına dair hesaplamalardan elde edilen miktarların doğrulanması ve şeffaf bir süreç oluşturulmasıdır.")
                
                pdf.ln(4)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.5. Hedef Kullanıcı", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Su ayak izi raporu hedef kullanıcıları; Firmamız Üst Yönetimi, Çalışanlar, Tedarikçiler ve Diğer Paydaşlardır.\nRapor, resmi kurumların talebi durumunda, sürdürülebilirlik raporlarına veri talebi durumunda ve küresel organizasyonların talebi durumunda ilgili kitlelere iletilir.")

                pdf.ln(4)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="1.6. Raporun ISO 14046:2014'e Uygunluğuna Dair Açıklama", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Su Ayakizi Raporu 'ISO 14046:2014 Water Footprint - Principles, Requirements and Guidelines' gereklerine uygun olarak yazılımımız tarafından otomatik hazırlanmıştır.")

                pdf.ln(6)
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="2. GENEL", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)

                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="2.1. Raporun Sahibi Olan Kuruluş ve Raporlama Dönemi", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"Raporun sahibi {str(company_name)} olup, rapor 01 Ocak {current_year} - 31 Aralık {current_year} tarih aralığı için hazırlanmıştır.")

                pdf.ln(4)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="2.2. Operasyonel Sınırlar", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt=f"Raporun Kuruluş bilgilerinde belirtilmiş olan adresimizdeki tüm operasyonlar sistem sınırlarına dahil edilmiştir. {str(company_name)} faaliyetlerinden kaynaklanan su kullanım ve su deşarjının %100'ü hesaplamalara dahil edilmiştir.\nBu çalışmada kapıdan kapıya (Gate-to-Gate) yaklaşımı uygulanmıştır.")

                # ==========================================
                # --- BÖLÜM 3: METODOLOJİ ---
                # ==========================================
                pdf.add_page()
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="3. METODOLOJİ", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="3.1. Veri Kalitesi", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Hesaplamalarda kullanılan şebeke ve kuyu suyu verisi sayaç tüketim kayıtlarından, diğer tatlı sular ise faturalardan alınmış olduğundan veri kalitesi yüksektir.")
                pdf.ln(3)
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="3.2. Kabuller", ln=True)
                pdf.set_font(f_isim, size=11, style='')
                pdf.multi_cell(190, 6, txt="Gri Su Ayak izi hesaplarında, üretim sonucu oluşan atıksuları hesaplarken laboratuvar analiz sonuçlarına göre en yüksek hacmi talep eden 'Kritik Kirletici' baz alınarak birincil veri kullanılmıştır.")

                pdf.ln(4)
                pdf.set_font(f_isim, size=11, style='B')
                pdf.cell(190, 8, txt="Tablo 2: Genel Akış - Sistem Sınırı", ln=True)
                
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(255, 192, 0) # Sarımtırak başlık
                pdf.cell(40, 8, txt="Bileşen", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="Kaynak", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="Veri Kaynağı", border=1, fill=True, align='C')
                pdf.cell(50, 8, txt="Veri Doğrulama", border=1, ln=True, fill=True, align='C')
                
                pdf.set_font(f_isim, size=10, style='')

                # Arayüzdeki dinamik tablonun her bir satırını okuyup PDF'e basan döngü
                for index, row in sistem_siniri_tablosu.iterrows():
                    # Eğer kullanıcı hücreyi boş bıraktıysa hata vermemesi için "-" yazdırıyoruz
                    bilesen = str(row["Bileşen"]) if pd.notna(row["Bileşen"]) else "-"
                    kaynak = str(row["Kaynak"]) if pd.notna(row["Kaynak"]) else "-"
                    veri_kaynagi = str(row["Veri Kaynağı"]) if pd.notna(row["Veri Kaynağı"]) else "-"
                    veri_dogrulama = str(row["Veri Doğrulama"]) if pd.notna(row["Veri Doğrulama"]) else "-"
                    
                    # Sadece içi tamamen boş olmayan satırları PDF'e ekle
                    if bilesen != "-" or kaynak != "-":
                        pdf.cell(40, 8, txt=bilesen, border=1, align='C')
                        pdf.cell(50, 8, txt=kaynak, border=1, align='C')
                        pdf.cell(50, 8, txt=veri_kaynagi, border=1, align='C')
                        pdf.cell(50, 8, txt=veri_dogrulama, border=1, ln=True, align='C')

                # ==========================================
                # --- BÖLÜM 4: HESAPLAMALAR ---
                # ==========================================
                pdf.ln(6)
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="4. HESAPLAMALAR", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)

                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4.1. Mavi Su Ayak İzi Hesaplamaları", ln=True)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt="Tesisin doğrudan tükettiği, buharlaştırdığı veya ürüne kattığı tatlı su miktarını temsil eder. Tesis giriş suyu ile deşarj arasındaki kütle denkliğine göre hesaplanmıştır.")
                
                pdf.ln(3)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(95, 8, txt="Veri Kaynağı", border=1, fill=True, align='C')
                pdf.cell(95, 8, txt="Toplam Tüketim (m³/yıl)", border=1, ln=True, fill=True, align='C')
                pdf.set_font(f_isim, size=10, style='')
                pdf.cell(95, 8, txt="Tesis Mavi Su Ayak İzi Hacmi", border=1, align='C')
                pdf.cell(95, 8, txt=f"{format_num(res_blue)}", border=1, ln=True, align='C')

                pdf.ln(5)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4.2. Yeşil Su Ayak İzi Hesaplamaları", ln=True)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt="Tesis sınırları içerisinde tüketilen veya ürüne katılan yağmur suyunu temsil eder.")
                
                pdf.ln(3)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(95, 8, txt="Veri Kaynağı", border=1, fill=True, align='C')
                pdf.cell(95, 8, txt="Toplam Tüketim (m³/yıl)", border=1, ln=True, fill=True, align='C')
                pdf.set_font(f_isim, size=10, style='')
                pdf.cell(95, 8, txt="Tesis Yeşil Su Ayak İzi Hacmi", border=1, align='C')
                pdf.cell(95, 8, txt=f"{format_num(res_green)}", border=1, ln=True, align='C')

                pdf.ln(5)
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt="4.3. Gri Su Ayak İzi Hesaplamaları", ln=True)
                pdf.set_font(f_isim, size=10, style='')
                pdf.multi_cell(190, 6, txt="Tesisten çıkan atıksudaki kirlilik yükünün, doğal alıcı ortam standartlarına kadar seyreltilmesi için gereken teorik tatlı su miktarını temsil eder. En kritik kirletici parametresi baz alınmıştır.")
                
                pdf.ln(3)
                pdf.set_font(f_isim, size=10, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(95, 8, txt="Bileşen / Kritik Kirletici", border=1, fill=True, align='C')
                pdf.cell(95, 8, txt="Gereken Seyreltme Hacmi (m³/yıl)", border=1, ln=True, fill=True, align='C')
                pdf.set_font(f_isim, size=10, style='')
                pdf.cell(95, 8, txt=f"Endüstriyel Atıksu (Kritik Kirletici)", border=1, align='C')
                pdf.cell(95, 8, txt=f"{format_num(res_grey)}", border=1, ln=True, align='C')

                # ==========================================
                # --- BÖLÜM 5: SONUÇ VE TAVSİYELER ---
                # ==========================================
                pdf.add_page()
                pdf.set_fill_color(0, 150, 136) 
                pdf.set_text_color(255, 255, 255) 
                pdf.set_font(f_isim, size=14, style='B')
                pdf.cell(190, 10, txt="5. SONUÇ", ln=True, align='L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)

                total_vol = res_blue + res_green + res_grey
                
                pdf.set_font(f_isim, size=12, style='B')
                pdf.cell(190, 8, txt=f"Toplam Tesis Su Ayak İzi: {format_num(total_vol)} m³/yıl", ln=True)
                pdf.ln(3)

                # Genel Dağılım Tablosu
                pdf.set_fill_color(0, 0, 128)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(70, 8, txt="Bileşen", border=1, align='C', fill=True)
                pdf.cell(70, 8, txt="Hacim (m³/yıl)", border=1, align='C', fill=True)
                pdf.cell(50, 8, txt="Dağılım (%)", border=1, ln=True, align='C', fill=True)
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(f_isim, size=11, style='')
                p_blue = (res_blue / total_vol) * 100 if total_vol > 0 else 0
                p_green = (res_green / total_vol) * 100 if total_vol > 0 else 0
                p_grey = (res_grey / total_vol) * 100 if total_vol > 0 else 0
                
                pdf.cell(70, 8, txt="Mavi Su", border=1, align='C')
                pdf.cell(70, 8, txt=f"{format_num(res_blue)}", border=1, align='C')
                pdf.cell(50, 8, txt=f"% {p_blue:,.1f}", border=1, ln=True, align='C')
                
                pdf.cell(70, 8, txt="Yeşil Su", border=1, align='C')
                pdf.cell(70, 8, txt=f"{format_num(res_green)}", border=1, align='C')
                pdf.cell(50, 8, txt=f"% {p_green:,.1f}", border=1, ln=True, align='C')
                
                pdf.cell(70, 8, txt="Gri Su", border=1, align='C')
                pdf.cell(70, 8, txt=f"{format_num(res_grey)}", border=1, align='C')
                pdf.cell(50, 8, txt=f"% {p_grey:,.1f}", border=1, ln=True, align='C')
                
                pdf.set_font(f_isim, size=11, style='B')
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(70, 8, txt="TOPLAM", border=1, align='C', fill=True)
                pdf.cell(70, 8, txt=f"{format_num(total_vol)}", border=1, align='C', fill=True)
                pdf.cell(50, 8, txt="% 100", border=1, ln=True, align='C', fill=True)

                pdf.ln(6) # Tablo ile grafik arasına biraz boşluk bırakalım

                           # --- PDF İÇİN TEMİZ VE MODERN DONUT GRAFİĞİ OLUŞTURMA ---
                etiketler = ['Mavi Su', 'Yesil Su', 'Gri Su'] 
                degerler = [res_blue, res_green, res_grey] 
                renkler = ['#678B99', '#8A9A70', '#C25946'] # Puslu Çini Mavisi, Mat Zeytin Yeşili, Klasik Kiremit
        
                # Eğer herhangi bir veri girilmişse grafiği çiz
                if sum(degerler) > 0:
                    # Temiz, düz zemin. shadow=False yaparak beğenmediğiniz efekti kaldırıyoruz.
                    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
                    
                    # width=0.3 ile ortasını boşaltıp "Halka" yapıyoruz
                    wedges, texts, autotexts = ax.pie(degerler, labels=etiketler, autopct='%1.1f%%', 
                                                     shadow=False, # Gölge yok, düz tasarım
                                                     startangle=90, 
                                                     colors=renkler, 
                                                     textprops={'fontsize': 10, 'weight': 'bold'}, 
                                                     pctdistance=0.85, 
                                                     wedgeprops=dict(width=0.3, edgecolor='w')) 
        
                    ax.axis('equal') # Grafiğin tam yuvarlak olmasını sağlar
                    ax.set_title("Toplam Tesis Su Ayak Izi Bilesimi", fontsize=12, fontweight='bold', pad=20)
                    
                    total = sum(degerler)
                    # Rakamı en basit ve garantili yöntemle tam ortaya yerleştiriyoruz
                    ax.text(0, 0, f"TOPLAM:\n{total:,.0f} m³", ha='center', va='center', fontsize=12, fontweight='bold')
        
                    # Grafik dosyası olarak kaydetme (Hafıza hatasını çözer)
                    grafik_yolu = "temp_grafik.png"
                    plt.savefig(grafik_yolu, format='png', dpi=300, bbox_inches='tight') 
                    plt.close(fig)
                    
                    # FPDF'e doğrudan dosya yolunu veriyoruz ki rfind hatası vermesin
                    pdf.image(grafik_yolu, x=35, y=pdf.get_y(), w=140) 
                    pdf.ln(100) # Grafiğin boyu kadar aşağı in
                
                # --- PDF İÇİNE HEDEFLERİ EKLEME BÖLÜMÜ ---
                gecerli_hedefler = [row for index, row in duzenlenmis_hedefler.iterrows() if str(row["Hedef Açıklaması"]).strip() != ""]
                
                if len(gecerli_hedefler) > 0:
                    pdf.ln(6)
                    pdf.set_fill_color(0, 150, 136) 
                    pdf.set_text_color(255, 255, 255) 
                    pdf.set_font(f_isim, size=14, style='B')
                    pdf.cell(190, 10, txt="6. SÜRDÜRÜLEBİLİRLİK HEDEFLERİ", ln=True, align='L', fill=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(5)
                    
                    pdf.set_font(f_isim, size=11, style='')
                    for i, hedef in enumerate(gecerli_hedefler):
                        hedef_metni = f"• {hedef['Hedef Yılı']} Yılı Hedefi: {hedef['Hedef Açıklaması']}"
                        pdf.multi_cell(190, 6, txt=hedef_metni)

                # ==========================================
                # --- FİZİKSEL DOSYA KAYDI VE İNDİRME ---
                # ==========================================
                gecici_dosya_adi = "gecici_rapor.pdf"
                pdf.output(gecici_dosya_adi)
                
                with open(gecici_dosya_adi, "rb") as pdf_dosyasi:
                    pdf_bytes = pdf_dosyasi.read()
                    
                st.download_button(
                    label="📄 PDF Raporunu İndir",
                    data=pdf_bytes,
                    file_name=f"Su_Ayak_Izi_Raporu_{str(company_name)}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Profesyonel PDF Oluşturma Hatası: {str(e)}")

                
    else:
        st.info("💡 Henüz kaydedilmiş bir raporunuz bulunmuyor.")

def sayfa_performans_kpi():
    st.header("📈 Tesis Performans Göstergeleri (KPI)")
    st.info("Bu bölümde tesisinizin proses ve evsel bazda spesifik su verimliliğini hesaplayabilirsiniz.")

    # --- EKSİK OLAN 1. KISIM: ÜRETİM VE PERSONEL VERİLERİ EKLENDİ ---
    st.subheader("1. Üretim ve Personel Verileri")
    col1, col2, col3, col4 = st.columns([2, 1, 2, 2]) 
    uretim_miktari = col1.number_input("Yıllık Üretim Miktarı", min_value=0.0, value=st.session_state.get('uretim_miktari', 0.0))
    
    birim_secenekleri = ["ton", "kg", "adet", "metre" "m²", "m³", "litre", "kutu"]
    varsayilan_birim = st.session_state.get('uretim_birimi', 'ton')
    secili_index = birim_secenekleri.index(varsayilan_birim) if varsayilan_birim in birim_secenekleri else 0
    uretim_birimi = col2.selectbox("Birim", options=birim_secenekleri, index=secili_index)
    
    calisma_gunu = col3.number_input("Yıllık Çalışma Günü", min_value=0.0, value=st.session_state.get('calisma_gunu', 0.0))
    personel_sayisi = col4.number_input("Personel Sayısı", min_value=0.0, value=st.session_state.get('personel_sayisi', 0.0))

    # --- 2. KISIM: SENİN HARİKA EKLENTİLERİN ---
    st.subheader("2. Evsel Su ve Diğer Su Tüketimleri")
    
    col5, col6, col7 = st.columns(3)
    evsel_su = col5.number_input("Evsel Su (m³/yıl)", min_value=0.0, value=st.session_state.get('evsel_su', 0.0))
    sulama_suyu = col6.number_input("Yeşil Alan Sulama (m³/yıl)", min_value=0.0, value=st.session_state.get('sulama_suyu', 0.0))
    yangin_suyu = col7.number_input("Yangın Hattı (m³/yıl)", min_value=0.0, value=st.session_state.get('yangin_suyu', 0.0))

    col8, col9, col10 = st.columns(3)
    arac_yikama = col8.number_input("Araç Yıkama/Zemin Temizliği vb. (m³/yıl)", min_value=0.0, value=st.session_state.get('arac_yikama', 0.0))
    gerikazanim_suyu = col9.number_input("Geri Kazanım Suyu (m³/yıl)", min_value=0.0, value=st.session_state.get('gerikazanim_suyu', 0.0))
    evsel_atiksu = col10.number_input("Evsel Atıksu Miktarı (m³/yıl)", min_value=0.0, value=st.session_state.get('evsel_atiksu', 0.0))

    # Ana hafızadan proses (endüstriyel) su verilerini otomatik çekiyoruz
    sebeke = st.session_state.get('sebeke_suyu', 0.0)
    kuyu = st.session_state.get('kuyu_suyu', 0.0)
    diger = st.session_state.get('diger_su', 0.0)
    toplam_giren_su = sebeke + kuyu + diger
    toplam_proses_atiksu = st.session_state.get('desarj', 0.0)

    st.divider()

    if st.button("📊 KPI Göstergelerini Hesapla", type="primary"):
        # Hafızaya Mühürleme İşlemleri
        st.session_state['uretim_miktari'] = uretim_miktari
        st.session_state['uretim_birimi'] = uretim_birimi
        st.session_state['calisma_gunu'] = calisma_gunu
        st.session_state['personel_sayisi'] = personel_sayisi
        st.session_state['evsel_su'] = evsel_su
        st.session_state['sulama_suyu'] = sulama_suyu
        st.session_state['yangin_suyu'] = yangin_suyu
        st.session_state['arac_yikama'] = arac_yikama
        st.session_state['gerikazanim_suyu'] = gerikazanim_suyu
        st.session_state['evsel_atiksu'] = evsel_atiksu

        # --- SENİN YENİ HESAPLAMA MANTIĞIN ---
        net_proses_suyu = max(0.0, toplam_giren_su - (evsel_su + sulama_suyu + yangin_suyu + arac_yikama + gerikazanim_suyu))

        # KPI Hesaplamaları
        spesifik_su = net_proses_suyu / uretim_miktari if uretim_miktari > 0 else 0
        spesifik_atiksu = toplam_proses_atiksu / uretim_miktari if uretim_miktari > 0 else 0
        
        payda_kisi_gun = calisma_gunu * personel_sayisi
        spesifik_evsel_su = (evsel_su * 1000) / payda_kisi_gun if payda_kisi_gun > 0 else 0
        spesifik_evsel_atiksu = (evsel_atiksu * 1000) / payda_kisi_gun if payda_kisi_gun > 0 else 0

        # Hafızaya alma
        st.session_state['kpi_net_proses'] = net_proses_suyu
        st.session_state['kpi_spesifik_su'] = spesifik_su
        st.session_state['kpi_spesifik_atiksu'] = spesifik_atiksu
        st.session_state['kpi_evsel_su'] = spesifik_evsel_su
        st.session_state['kpi_evsel_atiksu'] = spesifik_evsel_atiksu
        st.session_state['kpi_hesaplandi'] = True

    if st.session_state.get('kpi_hesaplandi', False):
        st.success("✅ Verimlilik Göstergeleri Başarıyla Hesaplandı!")
        
        st.markdown("#### Proses (Üretim) Verimliliği")
        c1, c2 = st.columns(2)
        birim = st.session_state.get('uretim_birimi', 'ton')
        
        c1.metric(label="Spesifik Su Tüketimi", 
                  value=f"{st.session_state['kpi_spesifik_su']:,.2f} m³/{birim}", 
                  delta=f"Hesaba Katılan Net Proses Suyu: {st.session_state['kpi_net_proses']:,.1f} m³", 
                  delta_color="off")
        c2.metric(label="Spesifik Atıksu Oluşumu", value=f"{st.session_state['kpi_spesifik_atiksu']:,.2f} m³/{birim}")

        st.markdown("#### Evsel (Personel) Verimliliği")
        c3, c4 = st.columns(2)
        c3.metric(label="Spesifik Evsel Su Tüketimi", value=f"{st.session_state['kpi_evsel_su']:,.2f} L/kişi.gün")
        c4.metric(label="Spesifik Evsel Atıksu Miktarı", value=f"{st.session_state['kpi_evsel_atiksu']:,.2f} L/kişi.gün")
        
# ==========================================
# 7. ANA KONTROL (ROUTER)
# ==========================================
def main():
    st.set_page_config(page_title="Su Ayak İzi Pro", page_icon="💧", layout="wide")
    add_bg_from_url()

    # ========================================================
    # --- 1. SİHİRLİ BAĞLANTI (URL) KONTROLÜ ---
    # ========================================================
    try:
        url_yetki = st.query_params.get("yetki", "")
        if url_yetki == "adaso_patron":
            st.session_state['admin_mi'] = True
        else:
            st.session_state['admin_mi'] = False
    except:
        st.session_state['admin_mi'] = False

    # ========================================================
    # --- 2. DİNAMİK SOL MENÜ OLUŞTURMA ---
    # ========================================================
    st.sidebar.title("Menü")
    
    sayfalar = ["🏠 Ana Sayfa", "🧮 Hesaplama", "📊 Veri Kalitesi","📈 Performans (KPI)", "📄 Raporlama", "🗄️ Geçmiş Raporlar", ]
    
    # Sadece linkte sihirli şifre varsa 3. seçeneği ekle
    if st.session_state.get('admin_mi', False):
        sayfalar.append("👑 Admin Paneli")
        
    page = st.sidebar.radio("Sayfa Seçiniz:", sayfalar)

    # ========================================================
    # --- 3. SAYFA YÖNLENDİRMELERİ (ROUTER) ---
    # ========================================================
    if page == "🏠 Ana Sayfa":
        show_home_page()
    elif page == "🧮 Hesaplama":
        show_calculator_page()
    elif page == "📊 Veri Kalitesi":
        sayfa_veri_kalitesi()
    elif page == "📈 Performans (KPI)":
        sayfa_performans_kpi()
    elif page == "📄 Raporlama":
        sayfa_raporlama()
    elif page == "🗄️ Geçmiş Raporlar":
        sayfa_gecmis_raporlar()
        
    # --- YENİ: GİZLİ ADMİN SAYFASI İÇERİĞİ ---
    elif page == "👑 Admin Paneli":
        
        st.subheader("📊 Sistemdeki Tüm Raporlar")
        
        try:
            # Supabase'den TÜM kayıtları çekiyoruz
            admin_response = supabase.from_("tesis_raporlari").select("*").order("olusturma_tarihi", desc=True).execute()
            
            if admin_response.data and len(admin_response.data) > 0:
                import pandas as pd
                df_admin = pd.DataFrame(admin_response.data)
                
                # 'id' sütununu gizleyip daha şık yapalım
                if "id" in df_admin.columns:
                    df_admin = df_admin.drop(columns=["id"])
                    
                st.metric(label="Sistemde Kayıtlı Toplam Rapor Sayısı", value=len(df_admin))
                st.dataframe(df_admin, use_container_width=True, hide_index=True)
            else:
                st.info("Sistemde henüz hiç kayıt bulunmuyor.")
                
        except Exception as e:
            st.error(f"Veritabanından veriler çekilirken bir hata oluştu: {str(e)}")

if __name__ == "__main__":
    main()
