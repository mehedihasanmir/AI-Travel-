from typing import List
from pydantic import BaseModel, Field


class ScheduleItem(BaseModel):
    time: str = Field(description="Time of day, e.g., Morning, Midday, Evening, Dinner")
    icon: str = Field(description="Emoji icon relevant to the activity")
    description: str = Field(description="Brief description of the activity")


class DayDetail(BaseModel):
    day: str = Field(description="Day identifier, e.g., 'Day 1'")
    title: str = Field(description="Theme title for the day")
    image_url: str = Field(description="Placeholder URL for the day's image (filled by tool)")
    schedule: List[ScheduleItem]


class StaticMap(BaseModel):
    image_url: str = Field(description="Placeholder URL for static map image (filled by tool)")
    description: str = Field(description="Description of what the map shows")


class TripDetails(BaseModel):
    static_map: StaticMap
    tour_spots_title: str = Field(default="Major Tour Spots", description="Title for the list of spots")
    tour_spots: List[str] = Field(description="List of names of major tourist spots visited")
    days: List[DayDetail]


class DaySummary(BaseModel):
    day: str
    title: str
    activities: List[str]


class Duration(BaseModel):
    days: int
    nights: int


class Buttons(BaseModel):
    view_details: bool = True
    share: bool = True
    save: bool = True


class TripOverview(BaseModel):
    title: str
    image_url: str = Field(description="Placeholder URL for cover image (filled by tool)")
    duration: Duration
    spots_count: int
    categories: List[str] = Field(description="List of categories like Beach, Nature, Food")
    description: str
    summary_itinerary: List[DaySummary]
    buttons: Buttons = Field(default_factory=Buttons)


class TripPlan(BaseModel):
    trip: TripOverview
    details: TripDetails
