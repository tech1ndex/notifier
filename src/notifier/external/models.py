from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class KeyImage(BaseModel):
    type: str
    url: str

class Seller(BaseModel):
    id: str
    name: str

class Item(BaseModel):
    id: str
    namespace: str

class CustomAttribute(BaseModel):
    key: str
    value: str

class Category(BaseModel):
    path: str

class Tag(BaseModel):
    id: str

class CatalogMapping(BaseModel):
    page_slug: str = Field(alias="pageSlug")
    page_type: str = Field(alias="pageType")

class CatalogNs(BaseModel):
    mappings: List[CatalogMapping]

class OfferMapping(BaseModel):
    page_slug: str = Field(alias="pageSlug")
    page_type: str = Field(alias="pageType")

class CurrencyInfo(BaseModel):
    decimals: int

class FmtPrice(BaseModel):
    original_price: str = Field(alias="originalPrice")
    discount_price: str = Field(alias="discountPrice")
    intermediate_price: str = Field(alias="intermediatePrice")

class TotalPrice(BaseModel):
    discount_price: int = Field(alias="discountPrice")
    original_price: int = Field(alias="originalPrice")
    voucher_discount: int = Field(alias="voucherDiscount")
    discount: int
    currency_code: str = Field(alias="currencyCode")
    currency_info: CurrencyInfo = Field(alias="currencyInfo")
    fmt_price: FmtPrice = Field(alias="fmtPrice")

class LineOfferRule(BaseModel):
    id: Optional[str] = None
    end_date: Optional[str] = Field(None, alias="endDate")
    discount_setting: Optional[dict] = Field(None, alias="discountSetting")

class LineOffer(BaseModel):
    applied_rules: List[LineOfferRule] = Field(alias="appliedRules")

class Price(BaseModel):
    total_price: TotalPrice = Field(alias="totalPrice")
    line_offers: List[LineOffer] = Field(alias="lineOffers")

class DiscountSetting(BaseModel):
    discount_type: str = Field(alias="discountType")
    discount_percentage: Optional[int] = Field(None, alias="discountPercentage")

class PromotionalOffer(BaseModel):
    start_date: datetime = Field(alias="startDate")
    end_date: datetime = Field(alias="endDate")
    discount_setting: DiscountSetting = Field(alias="discountSetting")

class PromotionalOfferGroup(BaseModel):
    promotional_offers: List[PromotionalOffer] = Field(alias="promotionalOffers")

class Promotions(BaseModel):
    promotional_offers: List[PromotionalOfferGroup] = Field(alias="promotionalOffers")
    upcoming_promotional_offers: List[PromotionalOfferGroup] = Field(alias="upcomingPromotionalOffers")

class EpicGameData(BaseModel):
    title: str
    id: str
    namespace: str
    description: str
    effective_date: datetime = Field(alias="effectiveDate")
    offer_type: str = Field(alias="offerType")
    expiry_date: Optional[datetime] = Field(None, alias="expiryDate")
    viewable_date: datetime = Field(alias="viewableDate")
    status: str
    is_code_redemption_only: bool = Field(alias="isCodeRedemptionOnly")
    key_images: List[KeyImage] = Field(alias="keyImages")
    seller: Seller
    product_slug: Optional[str] = Field(None, alias="productSlug")
    url_slug: str = Field(alias="urlSlug")
    url: Optional[str] = None
    items: List[Item]
    custom_attributes: List[CustomAttribute] = Field(alias="customAttributes")
    categories: List[Category]
    tags: List[Tag]
    catalog_ns: CatalogNs = Field(alias="catalogNs")
    offer_mappings: List[OfferMapping] = Field(alias="offerMappings")
    price: Price
    promotions: Promotions

class FormattedGame(BaseModel):
    game_title: str
    game_price: str
    end_date: datetime
    game_url: str

    class Config:
        allow_population_by_field_name = True