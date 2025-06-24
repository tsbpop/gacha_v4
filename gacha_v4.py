import streamlit as st
import pandas as pd
import random
from collections import defaultdict

st.title("구성품 수집 시뮬레이터 (소환 + 합성 + 리롤)")

# --- 입력 ---
uploaded_file = st.file_uploader("확률표 엑셀 업로드 (등급, 구성품, 확률)", type=["xlsx"])
gacha_cost = 2500
s_pity = 300
r_pity = 2000
limit_r_pity = True
num_simulation = st.number_input("시뮬레이션 반복 횟수", value=1, min_value=1)

# 소환 천장 수정할 수 있도록 변경
st.header("💡 소환 천장 설정")

# S등급 천장 (ex: 300회마다 S등급 1장)
s_pity = st.number_input("S등급 천장 횟수 (ex: 300회)", min_value=1, value=300)
# R등급 천장 (ex: 2000회 최초 1장 지급)
r_pity = st.number_input("R등급 천장 횟수 (최초 1회)", min_value=1, value=2000)
# R등급 천장 1회만 적용할지 여부
limit_r_pity = st.checkbox("R등급 천장은 최초 1회만 적용", value=True)

# 리롤 비용 설정 (등급별, 회차별)
reroll_costs = {
    "S": [13750, 20625, 34375],
    "R": [82500, 123750, 192500],
    "SR": [825000, 825000, 825000]
}
MAX_REROLL = 3

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df["확률"] = df["확률"] / 100  # 퍼센트 -> 소수

    all_items = {}
    for grade, group in df.groupby("등급"):
        all_items[grade] = set(group["구성품"])

    # SR 예외처리 (엑셀에 없으면 기본 10개 생성)
    if "SR" not in all_items:
        all_items["SR"] = set([f"SR_{i+1:02d}" for i in range(10)])

    items_list = (df["등급"] + ":" + df["구성품"]).tolist()
    probs_list = df["확률"].tolist()

    next_grade = {"C": "B", "B": "A", "A": "S", "S": "R", "R": "SR"}
    synth_rates = {"C": 0.25, "B": 0.21, "A": 0.18, "S": 0.16, "R": 0.15}
    synth_pity_limits = {"A": ("S", 20), "S": ("R", 15), "R": ("SR", 10)}

    def roll_with_reroll(grade, collection):
        reroll_count = 0
        while reroll_count < MAX_REROLL:
            candidate = random.choice(list(all_items[grade]))
            if candidate not in collection:
                return candidate, reroll_count + 1  # 리롤 성공, 몇 회차인지 반환 (1~3)
            reroll_count += 1
        # 최대 리롤 시도 후에도 중복
        return candidate, reroll_count  # 3회차 리롤 실패

    def simulate_until_complete(target_grade):
        collection = set()
        inventory = defaultdict(list)
        gacha_count = 0
        r_pity_used = False
        grade_summon_count = defaultdict(int)
        synth_pity_counter = defaultdict(int)
        total_reroll_cost = 0  # 리롤 비용 누적 변수

        while len(collection) < len(all_items[target_grade]):
            gacha_count += 1
            draw = random.choices(items_list, weights=probs_list, k=1)[0]
            grade, item = draw.split(":")

            # 소환 천장: S등급 300회 마다
            if gacha_count % s_pity == 0 and target_grade in ["S", "R", "SR"]:
                pity_item = random.choice(list(all_items["S"]))
                grade_summon_count["S"] += 1
                if pity_item not in collection:
                    if "S" == target_grade:
                        collection.add(pity_item)
                    else:
                        inventory["S"].append(pity_item)
                else:
                    inventory["S"].append(pity_item)

            # 소환 천장: R등급 2000회 최초 1회
            if gacha_count >= r_pity and not r_pity_used and target_grade in ["R", "SR"]:
                pity_item = random.choice(list(all_items["R"]))
                grade_summon_count["R"] += 1
                if pity_item not in collection:
                    if target_grade == "R":
                        collection.add(pity_item)
                    else:
                        inventory["R"].append(pity_item)
                else:
                    inventory["R"].append(pity_item)
                if limit_r_pity:
                    r_pity_used = True

            # 리롤 적용 (S, R, SR 등급 한정)
            if grade in ["S", "R", "SR"]:
                # target_grade 수집 중인 경우 중복시 리롤 시도
                if grade == target_grade:
                    if item in collection:
                        new_item, reroll_count = roll_with_reroll(grade, collection)
                        if reroll_count > 0:
                            reroll_cost = reroll_costs[grade][min(reroll_count - 1, MAX_REROLL - 1)]
                            total_reroll_cost += reroll_cost
                        item = new_item
                else:
                    # target_grade가 아니면 inventory 기준으로 중복 체크
                    if item in inventory[grade]:
                        new_item, reroll_count = roll_with_reroll(grade, inventory[grade])
                        if reroll_count > 0:
                            reroll_cost = reroll_costs[grade][min(reroll_count - 1, MAX_REROLL - 1)]
                            total_reroll_cost += reroll_cost
                        item = new_item

            # 일반 소환 결과 처리
            if grade == "SR":
                inventory[grade].append(item)
            else:
                if grade == target_grade and item not in collection:
                    collection.add(item)
                else:
                    inventory[grade].append(item)

            grade_summon_count[grade] += 1

            # 합성
            for g in ["C", "B", "A", "S", "R"]:
                while len(inventory[g]) >= 4:
                    inventory[g] = inventory[g][4:]
                    synth_pity_counter[g] += 1

                    if g in synth_pity_limits and synth_pity_counter[g] >= synth_pity_limits[g][1]:
                        pity_grade = synth_pity_limits[g][0]
                        pity_item = random.choice(list(all_items[pity_grade]))
                        if pity_grade == target_grade:
                            if pity_item not in collection:
                                collection.add(pity_item)
                            else:
                                inventory[pity_grade].append(pity_item)
                        else:
                            inventory[pity_grade].append(pity_item)
                        synth_pity_counter[g] = 0
                        continue

                    if random.random() < synth_rates[g]:
                        new_g = next_grade[g]
                        new_item = random.choice(list(all_items[new_g]))
                        if new_g == target_grade:
                            if new_item not in collection:
                                collection.add(new_item)
                            else:
                                inventory[new_g].append(new_item)
                        else:
                            inventory[new_g].append(new_item)
                    else:
                        fail_item = random.choice(list(all_items[g]))
                        inventory[g].append(fail_item)

        cost = gacha_count * gacha_cost + total_reroll_cost

        return {
            "collection": collection,
            "grade_summon_count": grade_summon_count,
            "gacha_count": gacha_count,
            "cost": cost,
            "reroll_cost": total_reroll_cost
        }

    if st.button("시뮬레이션 실행"):
        results = []
        for grade in ["S", "R", "SR"]:
            total_gacha = 0
            total_cost = 0
            total_reroll = 0

            with st.spinner(f"{grade} 등급 시뮬레이션 진행 중..."):
                for _ in range(num_simulation):
                    res = simulate_until_complete(grade)
                    total_gacha += res["gacha_count"]
                    total_cost += res["cost"]
                    total_reroll += res["reroll_cost"]

            avg_gacha = total_gacha / num_simulation
            avg_cost = total_cost / num_simulation
            avg_reroll = total_reroll / num_simulation

            results.append({
                "등급": grade,
                "평균 소환 횟수": round(avg_gacha),
                "기대 소환 비용 (원)": int(avg_cost - avg_reroll),
                "기대 리롤 비용 (원)": int(avg_reroll),
                "총 비용 (원)": int(avg_cost)
            })

        df_results = pd.DataFrame(results)
        df_results = df_results.style.format({
            "평균 소환 횟수": "{:,}",
            "기대 소환 비용 (원)": "{:,}",
            "기대 리롤 비용 (원)": "{:,}",
            "총 비용 (원)": "{:,}"
        })
        st.subheader("결과 요약 (표)")
        st.dataframe(df_results)

else:
    st.info("확률표 엑셀을 업로드해 주세요.")
