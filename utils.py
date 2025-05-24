import pandas as pd

FILE = 'courses.csv'

def load_courses():
    try:
        return pd.read_csv(FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "Course Code", "Course Name", "Description",
            "Prerequisites", "Co-requisites", "Credit Hours",
            "Semester Offered", "Track"
        ])

def save_courses(df):
    df.to_csv(FILE, index=False)

def get_course_list():
    df = load_courses()
    return df.to_dict(orient='records')

