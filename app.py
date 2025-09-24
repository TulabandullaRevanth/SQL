import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
from io import BytesIO

def mongo_to_df(mongo_list):
    df = pd.DataFrame(mongo_list)
    if "_id" in df.columns:
        df["_id"] = df["_id"].astype(str)
    return df
st.set_page_config(page_title="School Dashboard", layout="wide")
st.title("School Dashboard")

with st.sidebar.form("login_form"):
    username = st.text_input("Enter your username", "root")
    submitted = st.form_submit_button("Login")
if submitted:
    st.success(f"Hi, {username}! Welcome to the School Dashboard.")

with st.spinner("Loading data from MongoDB..."):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["schools_db"]
    students = list(db.students.find())
    courses = list(db.courses.find())
    enrollments = list(db.enrollments.find())

df_students = mongo_to_df(students)
df_courses = mongo_to_df(courses)
df_enrollments = mongo_to_df(enrollments)

if "age" not in df_students.columns:
    df_students["age"] = 0
if "course_name" not in df_courses.columns:
    df_courses["course_name"] = "Unknown"
if "instructor" not in df_courses.columns:
    df_courses["instructor"] = "Unknown"

df_merged = df_enrollments.merge(df_students, on="student_id", how="left") \
                          .merge(df_courses, on="course_id", how="left")

grade_cols = [c for c in df_merged.columns if "grade" in c.lower()]
if grade_cols:
    grade_col = grade_cols[0]
    df_merged[grade_col] = df_merged[grade_col].fillna("N/A")
else:
    grade_col = "grade"
    df_merged[grade_col] = "N/A"

st.sidebar.subheader("🔍 Filter Students & Enrollments")

course_col = "course_name"
instructor_col = "instructor"

course_options = df_merged[course_col].dropna().unique().tolist()
instructor_options = df_merged[instructor_col].dropna().unique().tolist()
grade_options = df_merged[grade_col].dropna().unique().tolist()

min_age = int(df_merged["age"].min()) if "age" in df_merged.columns else 0
max_age = int(df_merged["age"].max()) if "age" in df_merged.columns else 100

selected_courses = st.sidebar.multiselect("Select Course(s):", course_options, default=course_options)
selected_grades = st.sidebar.multiselect("Select Grade(s):", grade_options, default=grade_options)
age_range = st.sidebar.slider("Select Age Range:", min_age, max_age, value=(min_age, max_age))
selected_instructors = st.sidebar.multiselect("Select Instructor(s):", instructor_options, default=instructor_options)

filtered = df_merged[
    (df_merged[course_col].isin(selected_courses)) &
    (df_merged[grade_col].isin(selected_grades)) &
    (df_merged["age"].between(age_range[0], age_range[1])) &
    (df_merged[instructor_col].isin(selected_instructors))
]

st.subheader("Filtered Enrollments")
if filtered.empty:
    st.warning("No data found!")
else:
    st.dataframe(filtered)

with st.expander("Applied Filter"):
    st.code({
        "courses": selected_courses,
        "grades": selected_grades,
        "age_range": age_range,
        "instructors": selected_instructors
    })

st.subheader(" Key Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Students", filtered["student_id"].nunique())
col2.metric("Total Courses", filtered[course_col].nunique())
col3.metric("Average Age", round(filtered["age"].mean(), 1) if not filtered.empty else 0)
col4.metric("Enrollments Count", len(filtered))

# More insights
with st.expander("More insights: Top 5 popular courses"):
    top_courses = filtered.groupby(course_col)["student_id"].nunique().sort_values(ascending=False).head(5)
    st.table(top_courses.reset_index().rename(columns={"student_id": "Number of Students"}))

st.subheader("Edit Student Info")
if not filtered.empty:
    edited = st.data_editor(filtered[["student_id", "name", "age", grade_col]], num_rows="dynamic")
    if st.button("Update Changes"):
        for _, row in edited.iterrows():
            db.students.update_one({"student_id": row["student_id"]}, {"$set": {"age": row["age"], "grade": row.get(grade_col, "")}})
        st.success("Student records updated successfully!")

st.subheader(" Advanced Visualizations")
tab1, tab2, tab3 = st.tabs(["Enrollment Trends", "Grade Distribution", "Course Popularity"])

with tab1:
    st.markdown("**Enrollment Trends Over Time**")
    if "enrollment_date" in filtered.columns:
        filtered['enrollment_date'] = pd.to_datetime(filtered['enrollment_date'])
        trends = filtered.groupby(filtered['enrollment_date'].dt.to_period("M")).size().reset_index(name='count')
        trends['enrollment_date'] = trends['enrollment_date'].dt.to_timestamp()
        fig = px.line(trends, x='enrollment_date', y='count', title="Monthly Enrollment Trends")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No 'enrollment_date' column found.")

with tab2:
    st.markdown("**Number of Students per Grade**")
    grade_counts = filtered.groupby(grade_col)["student_id"].nunique().reset_index(name="student_count")
    fig = px.bar(grade_counts, x=grade_col, y="student_count", color="student_count", title="Students per Grade")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("**Students by Course**")
    course_counts = filtered.groupby(course_col)["student_id"].nunique().reset_index(name="student_count")
    fig = px.pie(course_counts, names=course_col, values="student_count", hole=0.4, title="Course Popularity")
    st.plotly_chart(fig, use_container_width=True)

if not filtered.empty:
    csv_bytes = filtered.to_csv(index=False).encode()
    st.download_button(
        label=" Download Filtered Students as CSV",
        data=csv_bytes,
        file_name="filtered_students.csv",
        mime="text/csv"
    )
