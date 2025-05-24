from experta import KnowledgeEngine, Fact, Rule, MATCH, AS, Field
import pandas as pd


class Student(Fact):
    cgpa = Field(float)
    semester = Field(str)
    passed = Field(list)
    failed = Field(list)

class Recommendation(Fact):
    pass

class CourseRecommender(KnowledgeEngine):
    def __init__(self, course_df):
        super().__init__()
        self.df = course_df
        self.recommendations = []
        self.total_credits = 0
        self.max_credits = 0
        self.explanations = []
        self.positive_explanations = []  # Store positive explanations

    def determine_credit_limit(self, cgpa):
        if cgpa < 2.0:
            return 12
        elif cgpa < 3.0:
            return 15
        return 18

    @Rule(Student(cgpa=MATCH.cgpa), salience=10)
    def set_credit_limit(self, cgpa):
        self.max_credits = self.determine_credit_limit(cgpa)
        self.explanations.append(f"Max credits set to {self.max_credits} based on CGPA {cgpa}")

    @Rule(AS.student << Student(passed=MATCH.passed, failed=MATCH.failed, semester=MATCH.sem),
          salience=0)
    def recommend_courses(self, student, passed, failed, sem):
        debug_log = []
        if self.df.empty:
            debug_log.append("No courses available in the database")
            self.explanations.extend(debug_log)
            return

        # Normalize passed and failed courses
        passed = [p.replace(" ", "") for p in passed]
        failed = [f.replace(" ", "") for f in failed]
        debug_log.append(f"Normalized Passed Courses: {passed}")
        debug_log.append(f"Normalized Failed Courses: {failed}")

        # Prioritize courses: Failed > Courses with met prerequisites > Others
        def course_priority(row):
            code = row["Course Code"]
            prereqs = [x.strip() for x in str(row["Prerequisites"]).split(",") if x.strip() and x != 'nan']
            if code in failed:
                return 0  # Highest priority for failed courses
            if prereqs and all(p in passed for p in prereqs):
                return 1  # Next priority for courses with met prerequisites
            return 2  # Lowest priority for courses with no prerequisites

        # Sort courses by priority
        sorted_df = self.df.copy()
        sorted_df['priority'] = sorted_df.apply(course_priority, axis=1)
        sorted_df = sorted_df.sort_values(by='priority')

        for _, row in sorted_df.iterrows():
            code = row["Course Code"]
            # Normalize code to ensure consistency
            code = code.replace(" ", "")
            name = row["Course Name"]
            track = row["Track"]
            prereqs = [x.strip() for x in str(row["Prerequisites"]).split(",") if x.strip() and x != 'nan']
            coreqs = [x.strip() for x in str(row["Co-requisites"]).split(",") if x.strip() and x != 'nan']
            semester_offered = row["Semester Offered"]
            try:
                credit = int(row["Credit Hours"])
            except (ValueError, TypeError):
                debug_log.append(f"Rejected {code} - Invalid credit hours: {row['Credit Hours']}")
                continue

            # Debug the passed course check
            debug_log.append(f"Checking if {code} is in passed: {code in passed}")
            if code in passed:
                debug_log.append(f"Rejected {code} - Already passed")
                continue

            # Validate course data
            if not code or pd.isna(code) or str(code).lower() == 'nan':
                debug_log.append(f"Rejected invalid course - Missing or invalid course code")
                continue
            if pd.isna(name) or str(name).lower() == 'nan':
                debug_log.append(f"Rejected {code} - Missing or invalid course name")
                continue
            if track != "Artificial Intelligence Engineering":
                debug_log.append(f"Rejected {code} - Not in AIE track")
                continue
            if semester_offered not in ["Fall", "Spring", "Both"]:
                debug_log.append(f"Rejected {code} - Invalid semester offered: {semester_offered}")
                continue
            if semester_offered != "Both" and semester_offered != sem:
                debug_log.append(f"Rejected {code} - Not offered in {sem}")
                continue

            # Check prerequisites
            debug_log.append(f"Checking prerequisites for {code}: {prereqs}")
            missing_prereqs = [p for p in prereqs if p not in passed]
            if missing_prereqs:
                debug_log.append(f"Rejected {code} - Missing prerequisites: {', '.join(missing_prereqs)}")
                continue

            # Check co-requisites
            missing_coreqs = [c for c in coreqs if c not in passed and c not in [r[0] for r in self.recommendations] and c != code]
            if missing_coreqs:
                debug_log.append(f"Rejected {code} - Missing co-requisites: {', '.join(missing_coreqs)}")
                continue

            # Check credit limit
            if self.total_credits + credit > self.max_credits:
                debug_log.append(f"Rejected {code} - Credit limit exceeded (current: {self.total_credits}, adding: {credit}, max: {self.max_credits})")
                continue

            # Generate positive explanations for accepted courses
            explanation = self._generate_positive_explanation(code, name, prereqs, coreqs, failed, passed, credit)
            
            # Add course to recommendations
            if code in failed:
                self.recommendations.insert(0, (code, name, credit))
                debug_log.append(f"Added {code} - Previously failed, prioritized")
            else:
                self.recommendations.append((code, name, credit))
                debug_log.append(f"Added {code} - Eligible")
            
            self.positive_explanations.append(explanation)
            self.total_credits += credit

        # Final validation: Ensure no passed courses are in recommendations
        self.recommendations = [(code, name, credit) for code, name, credit in self.recommendations if code not in passed]
        debug_log.append(f"Final Recommendations: {[(code, name, credit) for code, name, credit in self.recommendations]}")

        if not self.recommendations:
            debug_log.append("No courses recommended after applying all filters")
        self.explanations.extend(debug_log)

    def _generate_positive_explanation(self, code, name, prereqs, coreqs, failed, passed, credit):
        """Generate user-friendly explanations for why courses are recommended"""
        explanations = []
        
        # Priority explanation
        if code in failed:
            explanations.append(f"🔄 **{code} ({name})** is prioritized because you previously failed this course and need to retake it.")
        else:
            explanations.append(f"✅ **{code} ({name})** is recommended for your academic progress.")
        
        # Prerequisites explanation
        if prereqs:
            met_prereqs = [p for p in prereqs if p in passed]
            if met_prereqs:
                explanations.append(f"   📚 Prerequisites satisfied: You have successfully passed {', '.join(met_prereqs)}.")
        else:
            explanations.append(f"   📚 No prerequisites required - you can take this course immediately.")
        
        # Co-requisites explanation  
        if coreqs:
            explanations.append(f"   🔗 Co-requisites: {', '.join(coreqs)} (must be taken together or already passed).")
        
        # Credit information
        explanations.append(f"   💳 Credit hours: {credit}")
        
        return "\n".join(explanations)

    def get_recommendations(self):
        return self.recommendations, self.explanations
    
    def get_positive_explanations(self):
        """Get user-friendly explanations for recommended courses"""
        return self.positive_explanations