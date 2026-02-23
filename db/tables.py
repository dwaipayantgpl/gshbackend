# db/tables.py
import uuid
from piccolo.table import Table
from piccolo.columns import (
    UUID,
    Varchar,
    Boolean,
    Timestamptz,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)
from piccolo.columns.choices import Choice

# ---------- Choice sets (enums) ----------

ROLE_CHOICES = [
    Choice("seeker", "seeker"),
    Choice("helper", "helper"),
    Choice("both", "both"),
    Choice("admin", "admin")
]

CAPACITY_CHOICES = [
    Choice("personal", "personal"),
    Choice("institutional", "institutional")
]

JOB_TYPE_CHOICES = [
    Choice("part_time", "part_time"),
    Choice("full_time", "full_time"),
    Choice("one_time", "one_time"),
    Choice("subscription", "subscription"),
]

JOB_REQUEST_STATUS_CHOICES = [
    Choice("open", "open"),
    Choice("closed", "closed"),
    Choice("fulfilled", "fulfilled"),
    Choice("cancelled", "cancelled"),
]

JOB_APPLICATION_STATUS_CHOICES = [
    Choice("pending", "pending"),
    Choice("accepted", "accepted"),
    Choice("rejected", "rejected"),
    Choice("cancelled", "cancelled"),
]

JOB_STATUS_CHOICES = [
    Choice("accepted", "accepted"),
    Choice("in_progress", "in_progress"),
    Choice("completed", "completed"),
    Choice("cancelled", "cancelled"),
]


COMPLAINT_STATUS_CHOICES = [
    Choice("pending", "pending"),
    Choice("in_progress", "in_progress"),
    Choice("resolved", "resolved"),
    Choice("blocked", "blocked"), # Good to track if the issue led to a block
]

# ---------- Core identity ----------

class Account(Table):
    """
    Login + credentials.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    phone = Varchar(length=20, unique=True)
    password_hash = Varchar(length=255)
    created_at = Timestamptz()
    is_active = Boolean(default=True)


class Registration(Table):
    """
    Role + capacity (personal / institutional) for an account.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    account = ForeignKey(references=Account, unique = True)
    role = Varchar(length=16, choices=ROLE_CHOICES)
    capacity = Varchar(length=16, choices=CAPACITY_CHOICES)
    created_at = Timestamptz()
    is_online = Boolean(default=False)  # your 'presence'


# ---------- Seeker details ----------

class SeekerPersonal(Table):
    """
    Personal seeker profile.
    One-to-one with a personal Registration.
    """
    registration = ForeignKey(references=Registration, unique=True)
    name = Varchar(length=100)
    city = Varchar(length=100)
    area = Varchar(length=100)
    avg_rating = Numeric(null=True)
    rating_count = Integer(default=0)


class SeekerInstitutional(Table):
    """
    Institutional seeker profile.
    """
    registration = ForeignKey(references=Registration, unique=True)
    name = Varchar(length=200)
    city = Varchar(length=100)
    area = Varchar(length=100)
    institution_type = Varchar(length=100, null=True)
    phone = Varchar(length=20, null=True)
    avg_rating = Numeric(null=True)
    rating_count = Integer(default=0)


# ---------- Helper details ----------

class HelperPersonal(Table):
    """
    Personal helper profile.
    """
    registration = ForeignKey(references=Registration, unique=True)
    name = Varchar(length=100)
    age = Integer(null=True)
    faith = Varchar(length=50, null=True)
    languages = Varchar(length=255, null=True)  # comma-separated for now
    city = Varchar(length=100)
    area = Varchar(length=100)
    phone = Varchar(length=20, null=True)
    years_of_experience = Integer(null=True)
    avg_rating = Numeric(null=True)
    rating_count = Integer(default=0)


class HelperInstitutional(Table):
    """
    Institutional helper (e.g. agency, hospital, etc).
    """
    registration = ForeignKey(references=Registration, unique=True)
    name = Varchar(length=200)
    city = Varchar(length=100)
    address = Text()
    phone = Varchar(length=20, null=True)
    avg_rating = Numeric(null=True)
    rating_count = Integer(default=0)


# ---------- Services & skills ----------

class Service(Table):
    """
    What a seeker asks for (electrician, driver, etc.).
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    name = Varchar(length=100)
    description = Text(null=True)


class Skill(Table):
    """
    More granular ability (AC repair, ICU nursing, etc.).
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    name = Varchar(length=100)
    description = Text(null=True)


class HelperService(Table):
    """
    Many-to-many: which services a helper can provide.
    """
    helper = ForeignKey(references=Registration)  # helper registration
    service = ForeignKey(references=Service)

    class Meta:
        unique_together = (("helper", "service"),)


class HelperSkill(Table):
    """
    Many-to-many: which skills a helper has.
    """
    helper = ForeignKey(references=Registration)
    skill = ForeignKey(references=Skill)

    class Meta:
        unique_together = (("helper", "skill"),)


# ---------- Helper preferences & experience ----------

class HelperPreference(Table):
    """
    Preferred working conditions for a helper (personal or institutional).
    """
    registration = ForeignKey(references=Registration, unique=True)
    city = Varchar(length=100, null=True)
    area = Varchar(length=100, null=True)
    job_type = Varchar(length=20, choices=JOB_TYPE_CHOICES, null=True)


class HelperPreferredService(Table):
    """
    Many-to-many: preferred services (subset of HelperService).
    """
    registration = ForeignKey(references=Registration)
    service = ForeignKey(references=Service)

    class Meta:
        unique_together = (("registration", "service"),)


class HelperExperience(Table):
    """
    Experience items, both personal and institutional (distinguished by Registration.capacity).
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    registration = ForeignKey(references=Registration)
    year_from = Integer(null=True)
    year_to = Integer(null=True)
    service = ForeignKey(references=Service, null=True)
    city = Varchar(length=100, null=True)
    area = Varchar(length=100, null=True)
    description = Text(null=True)


# ---------- Jobs ----------

class JobRequest(Table):
    """
    What you called Jobrequirements.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    seeker = ForeignKey(references=Registration)
    headline = Varchar(length=200)
    description = Text()
    city = Varchar(length=100)
    area = Varchar(length=100)
    contact_phone = Varchar(length=20, null=True)
    job_type = Varchar(length=20, choices=JOB_TYPE_CHOICES)
    deadline_at = Timestamptz(null=True)
    status = Varchar(length=20, choices=JOB_REQUEST_STATUS_CHOICES, default="open")
    created_at = Timestamptz()


class JobRequestService(Table):
    """
    Many-to-many: services needed for a job request.
    """
    job_request = ForeignKey(references=JobRequest)
    service = ForeignKey(references=Service)

    class Meta:
        unique_together = (("job_request", "service"),)


class JobApplication(Table):
    """
    What you called applications.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    job_request = ForeignKey(references=JobRequest)
    helper = ForeignKey(references=Registration)
    status = Varchar(length=20, choices=JOB_APPLICATION_STATUS_CHOICES, default="pending")
    created_at = Timestamptz()


class Job(Table):
    """
    Confirmed engagement between seeker and helper for a JobRequest.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    job_request = ForeignKey(references=JobRequest)
    helper = ForeignKey(references=Registration)
    status = Varchar(length=20, choices=JOB_STATUS_CHOICES, default="accepted")
    agreed_price = Numeric(null=True)
    started_at = Timestamptz(null=True)
    completed_at = Timestamptz(null=True)


# ---------- Ratings ----------

class Rating(Table):
    """
    One rating from one user to another, usually tied to a Job.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    job = ForeignKey(references=Job)
    rater = ForeignKey(references=Registration)
    ratee = ForeignKey(references=Registration)
    score = Integer()
    review = Text(null=True)
    created_at = Timestamptz()


# ---------- Messaging ----------

class Message(Table):
    id = UUID(primary_key=True, default=uuid.uuid4)
    from_registration = ForeignKey(references=Registration)
    to_registration = ForeignKey(references=Registration)
    text = Text(null=True)
    created_at = Timestamptz()


class MessageAttachment(Table):
    id = UUID(primary_key=True, default=uuid.uuid4)
    message = ForeignKey(references=Message)
    file_path = Text()


# block list user
class BlacklistedUser(Table):
    phone = Varchar(length=20, unique=True)
    #reason = Text()
    banned_at = Timestamptz()

class BlockedUser(Table):
    # This links to your existing Account table
    account = ForeignKey(references=Account, unique=True) 
    #reason = Text()
    blocked_at = Timestamptz(auto_now=True)


# ---------- Complaint Table ----------
class Complaint(Table):
    """
    User submitted issues/complaints.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    account = ForeignKey(references=Account)
    subject = Varchar(length=100)
    description = Text()
    status = Varchar(length=20, choices=COMPLAINT_STATUS_CHOICES, default="pending")
    admin_note = Text(null=True)  # Added to store admin's reasoning
    created_at = Timestamptz(auto_now=True)

# ---------- seeker Helper preferences ----------
class SeekerPreference(Table):
    registration = ForeignKey(references=Registration)
    service = ForeignKey(references=Service)
    city = Varchar(length=100)
    area = Varchar(length=100)
    job_type = Varchar(length=20, choices=JOB_TYPE_CHOICES, null=True) 

    class Meta:
        unique_together = (("registration", "service"),)