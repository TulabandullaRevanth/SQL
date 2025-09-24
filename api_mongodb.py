from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId


class Student(BaseModel):
    student_id: int
    name: str
    age: int
    grade: str
    email: str


class Course(BaseModel):
    course_name: str
    instructor: str


class Enrollment(BaseModel):
    student_id: str
    course_id: str


app = FastAPI()

client = None
db = None


@app.on_event("startup")
def startup_db_client():
    global client, db
    client = MongoClient("mongodb://localhost:27017/")
    db = client["schools_db"]
    print("Connected to MongoDB: schools_db")


@app.on_event("shutdown")
def shutdown_db_client():
    client.close()
    print("MongoDB connection closed")


@app.get("/")
def home():
    return {
        "message": "Welcome! Connected to schools_db (students, courses, enrollments)"
    }


@app.post("/students")
def add_student(student: Student):
    student_dict = student.model_dump()
    result = db.students.insert_one(student_dict)
    student_dict["student_id"] = str(result.inserted_id)
    return student_dict


@app.post("/courses")
def add_course(course: Course):
    course_dict = course.model_dump()
    result = db.courses.insert_one(course_dict)
    course_dict["course_id"] = str(result.inserted_id)
    return course_dict


@app.get("/students")
def get_students():
    students = list(db.students.find())
    for s in students:
        s["student_id"] = str(s["_id"])
        del s["_id"]
    return students


@app.get("/courses")
def get_courses():
    courses = list(db.courses.find())
    for c in courses:
        c["course_id"] = str(c["_id"])
        del c["_id"]
    return courses


@app.post("/enrollments")
def add_enrollment(enrollment: Enrollment):
    student = db.students.find_one({"enrollment_id": ObjectId(enrollment.student_id)})

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    course = db.courses.find_one({"enrollment_id": ObjectId(enrollment.course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment_dict = {
        "student_id": ObjectId(enrollment.student_id),
        "course_id": ObjectId(enrollment.course_id),
    }
    result = db.enrollments.insert_one(enrollment_dict)

    return {
        "enrollment_id": str(result.inserted_id),
        "student_id": enrollment.student_id,
        "course_id": enrollment.course_id,
    }


@app.get("/enrollments")
def get_enrollments():
    enrollments = list(db.enrollments.find())
    output = []
    for e in enrollments:
        e["enrollment_id"] = str(e["_id"])
        del e["_id"]

        student = db.students.find_one({"_id": e["student_id"]})
        course = db.courses.find_one({"_id": e["course_id"]})

        e["student_id"] = str(e["student_id"])
        e["course_id"] = str(e["course_id"])

        e["student"] = (
            {"student_id": str(student["student_id"]), "name": student["name"]}
            if student
            else None
        )
        e["course"] = (
            {
                "course_id": str(course["course_id"]),
                "course_name": course["course_name"],
            }
            if course
            else None
        )

        output.append(e)
    return output


# 2.
@app.get("/")
def home():
    return {
        "message": "Welcome! Connected to schools_db (students, courses, enrollments)"
    }


@app.get("/databases")
def list_databases():
    try:
        databases = client.list_database_names()
        return {"databases": databases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3.


@app.post("/studentsnew")
def add_student(student: Student):
    try:
        student_dict = student.model_dump()
        result = db.students.insert_one(student_dict)
        student_dict["_id"] = str(result.inserted_id)
        return student_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/studentsnew")
def get_studentsnew():
    students = list(db.students.find())
    for s in students:
        s["student_id"] = str(s["_id"])
        del s["_id"]
    return students


# 4.
from fastapi import Path


@app.get("/students/{student_id}")
def get_student_by_id(
    student_id: str = Path(..., description="MongoDB ObjectId of the student")
):
    try:
        obj_id = ObjectId(student_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid student ID")

    student = db.students.find_one({"_id": obj_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student["student_id"] = str(student["_id"])
    del student["_id"]
    return student


# 5.
from fastapi import Query


@app.get("/students/search")
def search_students(
    name: str = Query(..., description="Name or part of the name to search")
):

    regex_pattern = {"$regex": name, "$options": "i"}

    students = list(db.students.find({"name": regex_pattern}))

    for s in students:
        s["student_id"] = str(s["_id"])
        del s["_id"]

    if not students:
        return {"message": "No students found matching the search criteria"}

    return students


# 6.
from fastapi import Body


@app.put("/studentsnew/{student_id}")
def update_student(student_id: str, student_update: Student = Body(...)):
    try:
        obj_id = ObjectId(student_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid student ID")

    update_data = student_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    result = db.students.update_one({"_id": obj_id}, {"$set": update_data})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")

    student = db.students.find_one({"_id": obj_id})
    student["student_id"] = str(student["_id"])
    del student["_id"]
    return student


# 7.
@app.delete("/studentsnew/{student_id}")
def delete_student(student_id: str):
    try:
        obj_id = ObjectId(student_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid student ID")

    student = db.students.find_one({"_id": obj_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    enrollment = db.enrollments.find_one({"student_id": obj_id})
    if enrollment:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete student: student is enrolled in a course",
        )

    db.students.delete_one({"_id": obj_id})
    return {"message": f"Student '{student['name']}' deleted successfully"}


# 8.
from bson import ObjectId


@app.get("/courses/{course_id}/students")
def get_students_in_course(course_id: str):
    try:
        obj_id = ObjectId(course_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid course ID")

    course = db.courses.find_one({"_id": obj_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")


# 9.
@app.get("/stats/grades")
def get_grade_stats():
    pipeline = [{"$group": {"_id": "$grade", "count": {"$sum": 1}}}]

    try:
        result = get_students().aggrigate(pipeline)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 10.
from collections import Counter


@app.get("/stats/top-courses")
def get_top_courses():
    try:
        enrollments = list(db.enrollments.find())

        course_counts = Counter(str(e["course_id"]) for e in enrollments)

        if not course_counts:
            return {"message": "No enrollments found"}

        courses = {str(c["_id"]): c for c in db.courses.find()}

        top_courses = []
        for course_id, count in course_counts.most_common():
            course = courses.get(course_id)
            if course:
                top_courses.append(
                    {
                        "course_id": course_id,
                        "course_name": course.get("course_name", "Unknown"),
                        "instructor": course.get("instructor", "Unknown"),
                        "enroll_count": count,
                    }
                )

        return top_courses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 11.
from fastapi import File, UploadFile
import pandas as pd
import io


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        students = df.to_dict(orient="records")

        if not students:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        result = db.students.insert_many(students)

        return {
            "message": f"{len(result.inserted_ids)} students uploaded successfully",
            "inserted_ids": [str(_id) for _id in result.inserted_ids],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 15.
from fastapi import Depends, Header, HTTPException, status

API_KEY = "secret123"


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


@app.get("/secure/data", dependencies=[Depends(verify_api_key)])
def secure_data():
    return {"message": "You have access to secure data!"}


# 16.
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime


class MongoLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1️⃣ Capture request details
        log_entry = {
            "method": request.method,
            "path": request.url.path,
            "timestamp": datetime.utcnow(),
        }

        try:
            db.logs.insert_one(log_entry)
        except Exception as e:
            print("Failed to log request:", e)

        response = await call_next(request)
        return response


# 17.
from fastapi import Cookie
from fastapi.responses import JSONResponse


@app.get("/set-name/{name}")
def set_name(name: str):
    response = JSONResponse(
        content={"message": f"Hello {name}, your name is saved in a cookie!"}
    )
    response.set_cookie(key="username", value=name)
    return response


@app.get("/welcome")
def welcome_user(username: str = Cookie(None)):
    if username:
        return {"message": f"Welcome back, {username}!"}
    else:
        return {"message": "Welcome! Please set your name first at /set-name/{name}."}


# 18.
from pymongo.errors import DuplicateKeyError


@app.exception_handler(DuplicateKeyError)
async def handle_duplicate_key(request: Request, exc: DuplicateKeyError):
    raise HTTPException(status_code=409, detail="Email already exists")


@app.post("/students")
def create_student(student: Student):
    inserted_id = db.insert_one(student.model_dump()).inserted_id
    return {"id": str(inserted_id), "name": student.name, "email": student.email}


@app.get("/students")
def list_students():
    return [
        {"id": str(s["_id"]), "name": s["name"], "email": s["email"]} for s in db.find()
    ]


# 19 .
@app.get("/students/paginated")
def get_students_paginated(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of students per page"),
):
    skip_count = (page - 1) * limit
    students_cursor = db.students.find().skip(skip_count).limit(limit)
    students = []
    for s in students_cursor:
        s["student_id"] = str(s["_id"])
        del s["_id"]
        students.append(s)

    total_students = db.students.count_documents({})
    total_pages = (total_students + limit - 1) // limit

    return {
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_students": total_students,
        "students": students,
    }


# 20.
from pymongo import MongoClient, ASCENDING, DESCENDING


@app.get("/students/filter")
def filter_and_sort_students(
    min_age: int = Query(0, ge=0, description="Minimum age to filter"),
    sort: str = Query(
        "asc", regex="^(asc|desc)$", description="Sort order: asc or desc"
    ),
):
    sort = sort.strip().lower()

    sort_order = ASCENDING if sort == "asc" else DESCENDING

    students_cursor = db.students.find({"age": {"$gte": min_age}}).sort(
        "age", sort_order
    )

    students = []
    for s in students_cursor:
        s["student_id"] = str(s["_id"])
        del s["_id"]
        students.append(s)

    return {
        "min_age": min_age,
        "sort_order": sort,
        "total_students": len(students),
        "students": students,
    }
