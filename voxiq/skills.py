"""Skill vocabulary: canonical name -> spoken/written variants.

Used to pull requirements out of a job description and to spot them in a spoken answer, where
Whisper may write "node js" or "sequel". Add your own lines; the match is on whole words.
"""
SKILLS = {
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript", "java script", "js"],
    "TypeScript": ["typescript", "type script"], "C++": ["c++", "c plus plus", "cpp"], "C": ["c language"],
    "C#": ["c#", "c sharp"], "Go": ["golang"], "Rust": ["rust"], "PHP": ["php"], "Kotlin": ["kotlin"],
    "SQL": ["sql", "sequel", "mysql", "postgresql", "postgres", "sqlite"], "MongoDB": ["mongodb", "mongo db", "mongo"],
    "Django": ["django"], "Flask": ["flask"], "FastAPI": ["fastapi", "fast api"], "Spring": ["spring boot", "spring"],
    "React": ["react", "reactjs", "react js"], "Angular": ["angular"], "Vue": ["vue", "vuejs"],
    "Node.js": ["node.js", "node js", "nodejs", "node"], "Express": ["express"],
    "HTML": ["html"], "CSS": ["css"], "REST APIs": ["rest api", "rest apis", "restful", "rest", "api", "apis"],
    "GraphQL": ["graphql"], "Git": ["git", "github", "gitlab"], "Docker": ["docker", "containers"],
    "Kubernetes": ["kubernetes", "k8s"], "AWS": ["aws", "amazon web services"], "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"], "Linux": ["linux"], "CI/CD": ["ci/cd", "ci cd", "continuous integration", "pipelines"],
    "Machine learning": ["machine learning", "ml"], "Deep learning": ["deep learning"], "NLP": ["nlp", "natural language processing"],
    "Computer vision": ["computer vision", "opencv"], "PyTorch": ["pytorch", "torch"], "TensorFlow": ["tensorflow"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"], "Pandas": ["pandas"], "NumPy": ["numpy"],
    "Data structures": ["data structures", "algorithms", "dsa"], "OOP": ["oop", "object oriented", "object-oriented"],
    "Testing": ["unit test", "unit tests", "unit testing", "testing", "pytest", "tdd"],
    "Agile": ["agile", "scrum"], "Data analysis": ["data analysis", "analytics", "data analytics"],
    "Excel": ["excel"], "Power BI": ["power bi", "powerbi"], "Tableau": ["tableau"],
    "Debugging": ["debugging", "debug", "debugged"], "Problem solving": ["problem solving", "problem-solving"],
    "Communication": ["communication", "communicate", "communicated"], "Teamwork": ["teamwork", "team player", "collaboration", "collaborate", "collaborated"],
    "Leadership": ["leadership", "led a team", "team lead"], "Ownership": ["ownership"],
    "Mentoring": ["mentoring", "mentored"], "Time management": ["time management", "deadlines", "deadline"],
    "Cybersecurity": ["cybersecurity", "cyber security", "security", "forensics"],
    "Android": ["android"], "iOS": ["ios", "swift"], "Flutter": ["flutter"],
    "Redis": ["redis"], "Kafka": ["kafka"], "Microservices": ["microservices", "microservice"],
    "System design": ["system design"], "Performance": ["performance", "optimization", "optimisation", "optimized", "optimised"],
}
