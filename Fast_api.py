from fastapi import FastAPI
import pandas as pd
from fastapi.responses import HTMLResponse

app = FastAPI()

students_df = pd.read_csv("./students.csv")
courses_df = pd.read_csv("./courses.csv")
enrollments_df = pd.read_csv("./enrollments.csv")


# 1. Getting the data
@app.get("/")
def home():
    return {"message": "Welcome! Use /students, /courses, or /enrollments"}


@app.get("/students")
def get_students():
    return students_df.to_dict(orient="records")


@app.get("/courses")
def get_courses():
    return courses_df.to_dict(orient="records")


@app.get("/enrollments")
def get_enrollments():
    return enrollments_df.to_dict(orient="records")


# 4.Fetch all students in tabular format


@app.get("/students_table", response_class=HTMLResponse)
def get_students_table():
    html_table = students_df.to_html(index=False)
    return f"""
    <html>
        <head>
            <title>Students Table</title>
        </head>
        <body>
            <h2>Students Data</h2>
            {html_table}
        </body>
    </html>
    """


# 5.
@app.get("/update-grade-form", response_class=HTMLResponse)
def update_grade_form():
    return """
    <html>
        <head>
            <title>Update Student Grade</title>
        </head>
        <body>
            <h2>Update Student Grade</h2>
            <form action="/update-grade" method="post">
                Student ID: <input type="number" name="student_id"><br><br>
                New Grade: <input type="text" name="grade"><br><br>
                <input type="submit" value="Update Grade">
            </form>
        </body>
    </html>
    """


# 9. Write a program to display students who are not enrolled in any course.
@app.get("/students_not_enrolled", response_class=HTMLResponse)
def get_students_not_enrolled():
    enrolled_ids = set(enrollments_df["student_id"].unique())

    not_enrolled_df = students_df[~students_df["student_id"].isin(enrolled_ids)]

    if not_enrolled_df.empty:
        return "<h3>All students are enrolled in at least one course.</h3>"

    html_table = not_enrolled_df.to_html(index=False)

    return f"""
    <html>
        <head><title>Students Not Enrolled</title></head>
        <body>
            <h2>Students not enrolled in any course</h2>
            {html_table}
        </body>
    </html>
    """


# 10.Perform an INNER JOIN between students and courses using Python to show student names along with the courses they are enrolled in.
@app.get("/students_courses", response_class=HTMLResponse)
def get_students_courses():
    merged_df = enrollments_df.merge(students_df, on="student_id").merge(
        courses_df, on="course_id"
    )

    if merged_df.empty:
        return "<h3>No enrollments found.</h3>"

    result_df = merged_df[
        ["student_id", "name", "course_id", "course_name", "instructor"]
    ]

    html_table = result_df.to_html(index=False)

    return f"""
    <html>
        <head><title>Students & Courses</title></head>
        <body>
            <h2>Students and Their Enrolled Courses</h2>
            {html_table}
        </body>
    </html>
    """


# 11. Write a Python function to search for a student by name (partial matches allowed using LIKE).
@app.get("/search_student/{student_name}", response_class=HTMLResponse)
def search_student(student_name: str):
    filtered_df = students_df[
        students_df["name"].str.contains(student_name, case=False, na=False)
    ]

    if filtered_df.empty:
        return f"<h3>No student found with name containing '{student_name}'</h3>"

    html_table = filtered_df.to_html(index=False)

    return f"""
    <html>
        <head><title>Search Student</title></head>
        <body>
            <h2>Search results for: {student_name}</h2>
            {html_table}
        </body>
    </html>
    """


# 13.Create a program to count how many students are enrolled per course and display results in descending order.
@app.get("/students_per_course", response_class=HTMLResponse)
def students_per_course():
    count_df = (
        enrollments_df.groupby("course_id").size().reset_index(name="student_count")
    )
    merged_df = count_df.merge(courses_df, on="course_id")

    sorted_df = merged_df.sort_values(by="student_count", ascending=False)

    html_table = sorted_df[
        ["course_id", "course_name", "instructor", "student_count"]
    ].to_html(index=False)

    return f"""
    <html>
        <head><title>Students per Course</title></head>
        <body>
            <h2>Number of Students Enrolled per Course (Descending)</h2>
            {html_table}
        </body>
    </html>
    """


# 14 .Write a Python script that accepts a course name as input and returns all enrolled students with their grades.
@app.get("/students_by_course/{course_name}", response_class=HTMLResponse)
def students_by_course(course_name: str):
    course = courses_df[courses_df["course_name"].str.lower() == course_name.lower()]
    if course.empty:
        return f"<h3>No course found with the name '{course_name}'</h3>"

    course_id = course.iloc[0]["course_id"]

    enrolled = enrollments_df[enrollments_df["course_id"] == course_id]
    merged = enrolled.merge(students_df, on="student_id")

    if merged.empty:
        return f"<h3>No students enrolled in '{course_name}'</h3>"

    html_table = merged[["student_id", "name", "grade"]].to_html(index=False)

    return f"""
    <html>
        <head><title>Students in {course_name}</title></head>
        <body>
            <h2>Students enrolled in: {course_name}</h2>
            {html_table}
        </body>
    </html>
    """
