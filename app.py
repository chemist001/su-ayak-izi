import streamlit as st
import pandas as pd
import datetime
import base64
import matplotlib.pyplot as plt
import io

# --- KÜTÜPHANE KONTROLLERİ ---
try:
    from fpdf import FPDF
except ModuleNotFoundError:
    st.error("⚠️ 'fpdf' kütüphanesi eksik. Terminale şunu yazın: python -m pip install fpdf")
    st.stop()

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    st.error("⚠️ 'matplotlib' kütüphanesi eksik. Terminale şunu yazın: python -m pip install matplotlib")
    st.stop()
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
    st.markdown(
         f"""
         <style>
         .stApp {{
             background-image: url("https://images.unsplash.com/photo-1518837695005-2083093ee35b?q=80&w=2070&auto=format&fit=crop");
             background-attachment: fixed;
             background-size: cover;
         }}
         div[data-testid="stVerticalBlock"] > div {{
             background-color: rgba(255, 255, 255, 0.96); 
             padding: 25px;
             border-radius: 12px;
             box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
         }}
         [data-testid="stSidebar"] {{
             background-color: rgba(240, 248, 255, 0.95); 
             border-right: 1px solid #b0c4de;
         }}
         h1 {{ color: #003366 !important; }}
         h2 {{ color: #004e92 !important; }}
         h3 {{ color: #006994 !important; }}
         
         .report-header {{
             background-color: #f0f2f6;
             padding: 10px;
             border-radius: 5px;
             border-left: 5px solid #004e92;
             margin-bottom: 10px;
             font-weight: bold;
             color: #333;
         }}
         </style>
         """,
         unsafe_allow_html=True
     )

# ==========================================
# 2. HESAPLAMA MOTORU (BACKEND)
# ==========================================
class WaterFootprintCalculator:
    
    def calculate_blue_water(self, v_in=0.0, v_discharge=0.0, same_basin=True, 
                             is_dry_process=False, evaporation=0.0, incorporation=0.0, lost_return=0.0):
        """
        WFN Mavi Su Ayak İzi Hesaplaması
        Öncelik Kütle Denkliğindedir (Mass Balance). 
        """
        # 1. İstisna: OSB Kuru Proses (Örn: Sadece evsel su kullanan tekstil/dokuma fabrikası)
        if is_dry_process and v_in > 0:
            return v_in * 0.10
            
        # 2. Yaklaşım: Kütle Denkliği (Giren ve çıkan su biliniyorsa)
        if v_in > 0 and v_discharge >= 0:
            if same_basin:
                # Aynı havzaya dönüyorsa, aradaki kayıp tüketimdir (Mavi Su)
                return max(0.0, v_in - v_discharge)
            else:
                # Farklı havzaya gidiyorsa, giren suyun tamamı kaybedilmiş (Mavi Su) sayılır
                return v_in
                
        # 3. Yaklaşım: Doğrudan WFN Temel Formülü (Eğer doğrudan sahadan bu veriler toplanabilmişse)
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
# 5. SAYFA İÇERİKLERİ (ESKİ TASARIM + YENİ ÖZELLİKLER)
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
    
    st.markdown("---")
    st.subheader("Su Ayak İzinin 3 Rengi")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🟦 Mavi Su")
        st.caption("Yüzey ve Yeraltı Suyu")
        st.write("""
        Mavi su ayak izi, doğrudan su kaynaklarından (akarsular, göller, yer altı suyu) kullanılan su miktarını ifade eder. Bu, suyun bir ürüne, hizmete veya süreçlere
        dahil edilmesi sırasında yapılan su çekimini temsil eder.

        * 🏭 Sanayi üretimi
        * 🚰 Evsel kullanım
        * 🌾 Tarımsal sulama
        """)
        
    with col2:
        st.markdown("### 🟩 Yeşil Su")
        st.caption("Yağmur Suyu")
        st.write("""
        Yeşil su ayak izi, bitkilerin büyümesi için kullanılan yağış suyunu ifade eder. Bu, toprak tarafından emilen ve bitkiler tarafından kullanılan su miktarını kapsar
        ve suyun doğal döngüsü içinde yer aldığı süreçleri değerlendirir. 

        * 🌲 Orman ürünleri
        * 🚜 Yağmurla beslenen tarım
        * 🌧️ Yağmur hasadı
        """)
        
    with col3:
        st.markdown("### ⬜ Gri Su")
        st.caption("Kirlilik Yükü")
        st.write("""
        Oluşan kirliliği, su kalitesi standartlarına (doğal konsantrasyona) seyreltmek için 
        gereken teorik temiz su miktarıdır. Bu, bir ürün veya süreç nedeniyle kirlenen suyun doğrudan veya dolaylı olarak temizlenmesi gereken su miktarını hesaplar.

        * 🧪 Kimyasal atıklar
        * 🚿 Atık su deşarjı
        """)
        
    st.markdown("---")

    st.title("📜 Su Verimliliği Yönetmeliği ve Belgelendirme")
    
    st.info("""27 Aralık 2024 tarihli ve 32765 sayılı Resmi Gazete'de yayımlanan 
    **Su Verimliliği Yönetmeliği** kapsamında, endüstriyel tesisler için 3 seviyeli bir 
    belgelendirme sistemi getirilmiştir.
    """)

    st.markdown("### 🏆 Belgelendirme Seviyeleri ve Kriterler")
    
    tab_mavi, tab_yesil, tab_turkuaz = st.tabs([
        "🟦 Mavi Belge (Temel)", 
        "🟩 Yeşil Belge (Verimlilik)", 
        "🩵 Turkuaz Belge (Mükemmeliyet)"
    ])

    with tab_mavi:
        st.header("Mavi Su Verimliliği Belgesi")
        st.write("Su verimliliği yönetim sistemini kuran tesislere verilir.")
        st.markdown("""
        **Gerekli Kriterler**
        * ✅ Su verimliliği konusunda sorumlu personel görevlendirilmesi.
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
        * ✅ **Yönetim Sistemi:** TS ISO 46001 Belgesine sahip olunması.
        """)
        st.warning("OSB'ler için yağmur suyu hasadı ve gri su kullanımı zorunludur.")

    with tab_turkuaz:
        st.header("Turkuaz Su Verimliliği Belgesi")
        st.write("Atık su geri kazanımı yapan tesislere verilir.")
        st.markdown("""
        **Endüstriyel Tesisler İçin Kriterler**
        * ✅ **Geri Kazanım:** Atık suyun en az **%20'sinin** geri kazanılarak yeniden kullanılması.
        * ✅ **Su Ayak İzi:** **TS EN ISO 14046 Su Ayak İzi** standardı kapsamında belgenin olması.
        * ✅ **NACE koduna uygun su verimliliği rehber dokümanlarında yer alan tekniklerin uygulanması.
        * ✅ **TSE tarafından verilen TS ISO 46001 Su Verimliliği Yönetim Sistemi Belgesine sahip olması.
        """)
        st.success("🌟 Bu uygulama, Turkuaz Belge için zorunlu olan **ISO 14046** hesaplamalarını yapar.")

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
    tab_firma, tab_mavi, tab_yesil, tab_gri, tab_veri, tab_sonuc = st.tabs([
        "🏢 Firma Profili", "🟦 Mavi Su", "🟩 Yeşil Su", "⬛ Gri Su", "📋Veri Kalitesi", "📊 Raporlama"
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
        
        duzenlenmis_sorumlular = st.data_editor(
            st.session_state['sorumlular_tablosu'], 
            num_rows="dynamic", 
            use_container_width=True,
            key="sorumlular_tablo_editor"
        )

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
        
        is_dry_process = st.checkbox("Tesis sadece evsel su tüketiyor (OSB Kuru Proses - %10 Varsayım)", value=st.session_state['kuru_proses'])
        st.session_state['kuru_proses'] = is_dry_process

    # --- 3. YEŞİL SU ---
    with tab_yesil:
        st.header("Yeşil Su Verileri")
        c1, c2 = st.columns(2)
        green_evap = c1.number_input("Yağmur Suyu (m³/yıl)", min_value=0.0, value=st.session_state['yesil_evap'])
        st.session_state['yesil_evap'] = green_evap
        
        green_incorp = c2.number_input("Ürüne Giren Yeşil Su (m³/yıl)", min_value=0.0, value=st.session_state['yesil_incorp'])
        st.session_state['yesil_incorp'] = green_incorp

    # --- 4. GRİ SU ---
    with tab_gri:
        st.header("Gri Su Verileri (Kritik Kirletici)")
        st.write("Laboratuvar analizlerinizdeki kirlilik parametrelerini aşağıya ekleyiniz. Sistem en kritik olanı seçecektir.")
        
        # Tabloyu doğrudan kalıcı hafızadan çağırıyor ve değişiklikleri kasaya kilitliyoruz
        duzenlenmis_df = st.data_editor(st.session_state['gri_tablo'], num_rows="dynamic", use_container_width=True)

    # --- 5. VERİ KALİTESİ VE SİSTEM SINIRI ---
    with tab_veri:
        st.header("Veri Kalitesi ve Sistem Sınırı")
        st.info("Lütfen tesisinize ait su bileşenlerini, kaynaklarını ve veri doğrulama yöntemlerini aşağıdaki tablodan seçiniz veya düzenleyiniz.")
    
        # 1. Aşama: Tablonun varsayılan (ilk açıldığında görünen) hali
        baslangic_verisi = pd.DataFrame(
        columns=["Bileşen", "Kaynak", "Veri Kaynağı", "Veri Doğrulama"]
    )

        baslangic_verisi.loc[0] = [None, None, None, None]
    
        # 2. Aşama: Tabloyu Streamlit'te etkileşimli (Excel gibi) hale getirme
        sistem_siniri_tablosu = st.data_editor(
            baslangic_verisi,
            column_config={
                "Bileşen": st.column_config.SelectboxColumn(
                    "Bileşen",
                    help="Suyun kategorisini seçin",
                    options=["Mavi Su", "Gri Su", "Yeşil Su"],
                    required=True
                ),
                "Kaynak": st.column_config.SelectboxColumn(
                    "Kaynak",
                    options=["Şebeke", "Kuyu", "Diğer", "Endüstriyel Atıksu"],
                    required=True
                ),
                "Veri Kaynağı": st.column_config.SelectboxColumn(
                    "Veri Kaynağı",
                    options=["Sayaç ve Fatura", "Analiz Raporları", "Sayaç", "Tahmin/Beyan"],
                    required=True
                ),
                "Veri Doğrulama": st.column_config.SelectboxColumn(
                    "Veri Doğrulama",
                    options=["Tüketim Kayıtları", "Fatura Kontrolü", "Laboratuvar Beyanı", "İç Kayıtlar"],
                    required=True
                )
            },
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True 
        )

    # --- 6. RAPORLAMA ---
    with tab_sonuc:
        st.header("Sonuç ve PDF Çıktısı")
        
    # Sadece kilidi açmak için butonu kullanıyoruz
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
                    is_dry_process=is_dry_process
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
                # ------------------------------------------------

                # ==========================================
                # --- 2. PROFESYONEL PDF İNDİRME MOTORU ---
                # ==========================================
                st.divider()
                
                def format_num(value):
                    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                try:
                    from fpdf import FPDF
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
                    pdf.cell(60, 8, txt="Raporlama Yılı", border=1, fill=True)
                    pdf.cell(130, 8, txt=f"{current_year}", border=1, ln=True)

                    pdf.ln(8)
                    pdf.set_font(f_isim, size=12, style='B')
                    pdf.cell(190, 8, txt="1.2. Tanımlar", ln=True)
                    pdf.set_font(f_isim, size=11, style='')
                    pdf.multi_cell(190, 6, txt="Mavi Su Ayak İzi: Bir ürünün tedarik zinciri boyunca mavi su kaynaklarının (yüzey ve yeraltı suyu) tüketimini ifade eder. 'Tüketim', su buharlaştığında, başka bir toplama alanına veya denize döndüğünde mevcut yerüstü su kütlesinden su kaybını ifade eder.\n\nYeşil Su Ayak İzi: Bir faaliyette kullanım için ihtiyaç duyulan yağmur suyudur.\n\nGri Su Ayak İzi: Kirliliği ifade eder ve mevcut çevre su kalitesi standartlarına dayanarak kirletici yükünü asimile etmek için gereken tatlı su hacmi olarak tanımlanır.")

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
                        label="📄 Profesyonel Kurumsal PDF Raporunu İndir",
                        data=pdf_bytes,
                        file_name=f"Su_Ayak_Izi_Raporu_{str(company_name)}.pdf",
                        mime="application/pdf"
                    )

                except Exception as e:
                    st.error(f"Profesyonel PDF Oluşturma Hatası: {str(e)}")

# ==========================================
# 7. ANA KONTROL (ROUTER)
# ==========================================
def main():
    st.set_page_config(page_title="Su Ayak İzi Pro", page_icon="💧", layout="wide")
    add_bg_from_url()
    
    st.sidebar.title("Menü")
    page = st.sidebar.radio("Sayfa Seçiniz:", ["🏠 Ana Sayfa", "🧮 Hesaplama"])
    
    st.sidebar.info("Geliştirici: Erdem Polat")

    if page == "🏠 Ana Sayfa":
        show_home_page()
    elif page == "🧮 Hesaplama":
        show_calculator_page()

if __name__ == "__main__":
    main()
