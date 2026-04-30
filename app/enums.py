from enum import Enum


class Role(Enum):
    ADMIN = "Admin"
    USER = "User"


class AssetType(Enum):
    LAPTOP = "Laptop"
    MONITOR = "Monitor"
    KEYBOARD = "Keyboard"
    MOUSE = "Mouse"
    HEADPHONES = "Headphones"
    MICROPHONE = "Microphone"
    WEBCAM = "Webcam"
    LICENSE = "License"


class Status(Enum):
    AVAILABLE = "Available"
    ASSIGNED = "Assigned"
    RETURNED = "Returned"
    UNDER_MAINTENANCE = "Under Maintenance"
    RETIRED = "Retired"


class RequestStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class Department(Enum):
    CP = "Customer and Products"
    STS = "Supply, Trading and Shipping"
    TECHNOLOGY = "Technology"
    FINANCE = "Finance"
    LEGAL = "Legal"
    HR = "Human Resources"


class AuditAction(Enum):
    LOGIN_SUCCESS = "Login Success"
    LOGIN_FAILED = "Login Failed"
    LOGOUT = "Logout"
    USER_CREATED = "User Created"
    USER_UPDATED = "User Updated"
    USER_DELETED = "User Deleted"
    ASSET_CREATED = "Asset Created"
    ASSET_UPDATED = "Asset Updated"
    ASSET_DELETED = "Asset Deleted"
    ASSET_ASSIGNED = "Asset Assigned"
    ASSET_RETURNED = "Asset Returned"
    ASSET_REQUEST_SUBMITTED = "Asset Request Submitted"
    ASSET_REQUEST_APPROVED = "Asset Request Approved"
    ASSET_REQUEST_REJECTED = "Asset Request Rejected"
    ASSET_REQUEST_UPDATED = "Asset Request Updated"
    ASSET_REQUEST_DELETED = "Asset Request Deleted"
