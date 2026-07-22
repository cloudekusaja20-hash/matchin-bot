from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    choosing_language = State()
    choosing_gender = State()
    choosing_preference = State()
    entering_name = State()
    entering_age = State()
    entering_location = State()
    entering_bio = State()
    uploading_photo = State()


class Verification(StatesGroup):
    uploading_video_note = State()


class EditProfile(StatesGroup):
    choosing_field = State()
    entering_value = State()
    uploading_photo = State()


class SwipeMessage(StatesGroup):
    waiting_message = State()


class VipPurchase(StatesGroup):
    waiting_proof = State()


class ReportUser(StatesGroup):
    waiting_reason = State()
