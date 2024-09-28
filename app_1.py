import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
# import japanize_matplotlib
import pulp
from ShiftScheduler import ShiftScheduler
ss = ShiftScheduler()

# セッション状態の初期化
if 'optimization_done' not in st.session_state:
    st.session_state.optimization_done = False
    st.session_state.shift_scheduler = None

# タイトル
st.title("シフトスケジューリングアプリ")

# サイドバー
st.sidebar.header("データのアップロード")

upload_calendar = st.sidebar.file_uploader("カレンダー")
upload_staff = st.sidebar.file_uploader("スタッフ")
# 開発中のみ
# upload_calendar = "../data/calendar.csv"
# upload_staff = "../data/staff.csv"

# タブ
tab1, tab2, tab3 = st.tabs(["カレンダー情報", "スタッフ情報", "シフト表作成"])

with tab1:
    if upload_calendar is not None:
        df_calendar = pd.read_csv(upload_calendar)
        st.markdown("## カレンダー情報")
        st.write(df_calendar)
    else:
        st.write('カレンダー情報をアップロードしてください')

with tab2:
    if upload_staff is not None:
        df_staff = pd.read_csv(upload_staff)
        st.markdown("## スタッフ情報")
        st.write(df_staff)
        if upload_calendar is not None:
            st.markdown("## 休暇希望")
            staff_ng_date_radio_button = {}
            # スタッフごとに休暇希望のラジオボタンを作成
            for i in range(len(df_staff)):
                staff_id = df_staff.loc[i, "スタッフID"]
                st.write()
                staff_ng_date_radio_button[staff_id] = st.radio(
                    staff_id,
                    ["すべてOK"]
                    + [
                        df_calendar.loc[j, "日付"]
                        for j in range(df_calendar.shape[0])
                    ],
                    horizontal=True,
                )
            # st.write(staff_ng_date_radio_button)

    else:
        st.write('スタッフ情報をアップロードしてください')

with tab3:
    if not upload_calendar:
        st.warning("カレンダー情報をアップロードしてください")
    if not upload_staff:
        st.warning("スタッフ情報をアップロードしてください")
    if upload_calendar and upload_staff:
        # スタッフごとの重み付け設定
        staff_penalty = {}
        for i, row in df_staff.iterrows():
            staff_penalty[row["スタッフID"]] = st.slider(
                f"{row['スタッフID']}の希望違反ペナルティ",
                0,
                100,
                50,
                key=row["スタッフID"],
            )   

        # 希望休暇ペナルティをStreamlitのレバーで設定
        penalty_off = st.slider("希望休暇ペナルティ", 0, 100, 50)

        optimize_button = st.button("最適化実行")

        if optimize_button:
            ss.set_data(
                df_staff,
                df_calendar,
                staff_penalty,
                staff_ng_date_radio_button,
                penalty_off,
            )
            ss.build_model()
            ss.solve()
            st.session_state.optimization_done = True
            st.session_state.shift_scheduler = ss

        if st.session_state.optimization_done:
            ss = st.session_state.shift_scheduler
            
            st.markdown("## 最適化結果")
            
            st.write("実行ステータス:", pulp.LpStatus[ss.status])
            st.write("最適値:", ss.model.objective.value())
            
            st.markdown("## シフト表")
            st.table(ss.sch_df)
            
            st.markdown("## シフト数の充足確認")
            # 各スタッフの合計シフト数をbar chartで表示
            shift_sum = ss.sch_df.sum(axis=1)
            st.bar_chart(shift_sum)
            
            st.markdown("## スタッフの希望の確認")
            # 各日の合計スタッフ数をbar chartで表示
            staff_sum = ss.sch_df.sum(axis=0)
            st.bar_chart(staff_sum)
            
            # 各日の合計責任者数をbar chartで表示
            st.markdown("## 責任者の合計シフト数の充足確認")
            # shift_scheduleにdf_staffをマージして責任者の合計シフト数を計算
            shift_schedule_with_staff_data = pd.merge(
                ss.sch_df,
                df_staff,
                left_index=True,
                right_on="スタッフID",
            )
            # 責任者フラグが1の行のみqueryで抽出
            shift_chief_only = shift_schedule_with_staff_data.query("責任者フラグ == 1")
            # 不要な列はdropで削除する
            shift_chief_only = shift_chief_only.drop(
                columns=[
                    "スタッフID",
                    "責任者フラグ",
                    "希望最小出勤日数",
                    "希望最大出勤日数",
                ]
            )
            shift_chief_sum = shift_chief_only.sum(axis=0)
            st.bar_chart(shift_chief_sum)
            
            # ダウンロードボタン表示
            st.download_button(
                label="シフト表をダウンロード",
                data=ss.sch_df.to_csv().encode("utf-8"),
                file_name="output.csv",
                mime="text/csv",
            )
      

