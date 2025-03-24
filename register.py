import streamlit as st
import pandas as pd
from firebase import firebase
from datetime import datetime

# Firebase connection
firebase = firebase.FirebaseApplication(
    'https://check-4c4c4-default-rtdb.asia-southeast1.firebasedatabase.app/',
    None
)

# ฟังก์ชันดึงข้อมูลจาก Firebase และแปลงเป็น DataFrame
@st.cache_data
def fetch_data():
    result_pass = firebase.get('/Pass/MAC ID', None)
    result_ng = firebase.get('/NG/MAC ID', None)

    def convert_to_dataframe(result, status):
        if result:
            data_list = []
            for key, value in result.items():
                if isinstance(value, dict):
                    value['ID'] = key
                    value['Status'] = status
                    if status == 'NG' and 'Location' not in value:
                        value['Location'] = 'N/A'
                    data_list.append(value)
                else:
                    data_dict = {'ID': key, 'Value': value, 'Status': status, 'Location': 'N/A'}
                    data_list.append(data_dict)
            return pd.DataFrame(data_list)
        return pd.DataFrame()

    df_pass = convert_to_dataframe(result_pass, 'Pass')
    df_ng = convert_to_dataframe(result_ng, 'NG')

    return pd.concat([df_pass, df_ng], ignore_index=True)

df = fetch_data()

# ฟังก์ชันค้นหา MAC ID ที่ตรงกัน
def search(MAC):
    if MAC:
        df_mac_filtered = df[df['ID'] == MAC]
        if not df_mac_filtered.empty:
            df_mac_filtered = df_mac_filtered.drop(columns=['ID'])  # ไม่ต้องแสดง ID ซ้ำ
            df_topic_value = df_mac_filtered.T.reset_index()
            df_topic_value.columns = ["Topic", "Value"]
            exclude_topics = ["User", "Status"]
            df_topic_value = df_topic_value[~df_topic_value["Topic"].isin(exclude_topics)]
            st.dataframe(df_topic_value, use_container_width=True)
        else:
            st.warning(f"⚠️ ไม่พบข้อมูลสำหรับ MAC ID: `{MAC}`")

# UI Streamlit
st.title("🔍 ดูผลทดสอบ/ลงทะเบียน")

# กำหนดค่าเริ่มต้นของ status ใน session_state
if 'status' not in st.session_state:
    st.session_state.status = False  # ค่าเริ่มต้นเป็น False

if 'status2' not in st.session_state:
    st.session_state.status2 = False  # ค่าเริ่มต้นเป็น False

left, right = st.columns(2)
# สร้างปุ่ม "ผลเทส" และสลับค่า status เมื่อกดปุ่ม
if left.button("ผลเทส"):
    st.session_state.status = not st.session_state.status  # Toggle ค่าระหว่าง True/False
    st.session_state.status2 = False

if right.button("ลงทะเบียน"):
    st.session_state.status2 = not st.session_state.status2
    st.session_state.status = False
# ถ้า status เป็น True ให้แสดง UI การเลือก MAC ID
if st.session_state.status and not st.session_state.status2:

    # สร้าง Selectbox ที่ดึงค่าจากฐานข้อมูล
    mac_list = df["ID"].tolist()  # ดึง MAC ID ทั้งหมดจากฐานข้อมูล
    selected_mac = st.selectbox("เลือก MAC ID:", [""] + mac_list, index=None)  # เพิ่มค่าว่างให้เลือก

    # ถ้าผู้ใช้เลือก MAC ID ให้แสดงข้อมูล
    if selected_mac:
        search(selected_mac)
if st.session_state.status2 and not st.session_state.status:
    mac_list = df["ID"].tolist()  # ดึง MAC ID ทั้งหมดจากฐานข้อมูล
    selected_mac = st.selectbox("เลือก MAC ID:", [""] + mac_list, index=None)

    if selected_mac:
        local_list = firebase.get('/Location', None)
        # ตรวจสอบว่ามีข้อมูลใน local_list หรือไม่
        if local_list:
            # เพิ่ม "Other" ในตัวเลือก selectbox
            selected_local = st.selectbox("เลือก Location:", [""] + list(local_list.values()) + ["Other"], index=None)
            regis_date = df.loc[df["ID"] == selected_mac, "date_regis"].values
            local_date = df.loc[df["ID"] == selected_mac, "Localtion"].values
            local_date_str = str(local_date).strip("[]").replace("'", "")
            # ถ้าเลือก "Other" ให้แสดง text input สำหรับพิมพ์ข้อมูลเอง
            if selected_local == "Other":
                custom_location = st.text_input("กรุณาพิมพ์ Location:")
                if custom_location:
                    firebase.post('/Location', custom_location)
                    if not (regis_date  == "" or regis_date is None):
                        st.warning(f"MAC ID `{selected_mac}` ได้รับการลงทะเบียนใช้งานแล้ว โดย {local_date_str}.\n\nหากท่านต้องการทำการแก้ไขข้อมูล กรุณาติดต่อ MIC Division")
                    else:
                        if st.button("ลงทะเบียน", key="register_button"):
                            firebase.put(f'/Pass/MAC ID/{selected_mac}','Localtion' ,custom_location)
                            current_date = datetime.now().strftime("%d/%m/%y")
                            firebase.put(f'/Pass/MAC ID/{selected_mac}','date_regis' ,current_date)
            elif selected_local:
                if not (regis_date  == "" or regis_date is None):
                    st.warning(f"MAC ID `{selected_mac}` ได้รับการลงทะเบียนใช้งานแล้ว โดย {local_date_str}.\n\nหากท่านต้องการทำการแก้ไขข้อมูล กรุณาติดต่อ MIC Division")
                else:
                    if st.button("ลงทะเบียน", key="register_button"):
                        firebase.put(f'/Pass/MAC ID/{selected_mac}','Localtion' ,selected_local)
                        current_date = datetime.now().strftime("%d/%m/%y")
                        firebase.put(f'/Pass/MAC ID/{selected_mac}','date_regis' ,current_date)
        else:
            st.write("ไม่พบข้อมูล Location")
