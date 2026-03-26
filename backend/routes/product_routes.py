from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from database import db, UPLOADS_DIR
from auth import get_current_user, get_admin_user
from models.schemas import (
    Brand, BrandCreate, BrandUpdate,
    Product, ProductCreate, ProductUpdate, StockAdjustment,
    ReviewCreate, ReviewResponse
)
from services.order_service import _save_base64_image
from limiter import limiter, get_user_id_or_ip
from datetime import datetime
from pathlib import Path
from bson import ObjectId
from typing import List, Optional
import uuid

router = APIRouter()

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# ==================== BRAND ENDPOINTS ====================

@router.get("/brands", response_model=List[Brand])
async def get_brands(active_only: bool = False):
    query = {"isActive": True} if active_only else {}
    brands = await db.brands.find(query).to_list(1000)
    result = []
    for brand in brands:
        product_count = await db.products.count_documents({"brandId": str(brand["_id"])})
        result.append(Brand(
            id=str(brand["_id"]),
            name=brand["name"],
            image=brand.get("image"),
            isActive=brand.get("isActive", True),
            productCount=product_count
        ))
    return result


@router.post("/brands", response_model=Brand)
async def create_brand(brand: BrandCreate, admin=Depends(get_admin_user)):
    brand_dict = brand.dict()
    brand_dict["createdAt"] = datetime.utcnow()
    result = await db.brands.insert_one(brand_dict)
    return Brand(
        id=str(result.inserted_id),
        name=brand.name,
        image=brand.image,
        isActive=brand.isActive,
        productCount=0
    )


@router.patch("/brands/{brand_id}", response_model=Brand)
async def update_brand(brand_id: str, brand_data: BrandUpdate, admin=Depends(get_admin_user)):
    update_dict = {k: v for k, v in brand_data.dict().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.brands.update_one({"_id": ObjectId(brand_id)}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    if "name" in update_dict:
        await db.products.update_many(
            {"brandId": brand_id},
            {"$set": {"brandName": update_dict["name"]}}
        )
    brand = await db.brands.find_one({"_id": ObjectId(brand_id)})
    product_count = await db.products.count_documents({"brandId": brand_id})
    return Brand(
        id=str(brand["_id"]),
        name=brand["name"],
        image=brand.get("image"),
        isActive=brand.get("isActive", True),
        productCount=product_count
    )


@router.delete("/brands/{brand_id}")
async def delete_brand(brand_id: str, admin=Depends(get_admin_user)):
    product_count = await db.products.count_documents({"brandId": brand_id})
    if product_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete brand with {product_count} products. Reassign or delete products first."
        )
    result = await db.brands.delete_one({"_id": ObjectId(brand_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    return {"message": "Brand deleted successfully"}


# ==================== PRODUCT ENDPOINTS ====================

@router.get("/products", response_model=List[Product])
async def get_products(
    category: Optional[str] = None,
    brand_id: Optional[str] = None,
    active_only: bool = True,
    in_stock_only: bool = False
):
    query = {}
    if active_only:
        query["isActive"] = True
    if in_stock_only:
        query["stock"] = {"$gt": 0}
    if category:
        query["category"] = category
    if brand_id:
        query["brandId"] = brand_id
    products = await db.products.find(query).to_list(1000)
    return [Product(id=str(p["_id"]), **{k: v for k, v in p.items() if k not in ("_id", "id")}) for p in products]


@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(id=str(product["_id"]), **{k: v for k, v in product.items() if k not in ("_id", "id")})


@router.post("/products", response_model=Product)
async def create_product(product: ProductCreate, admin=Depends(get_admin_user)):
    brand = await db.brands.find_one({"_id": ObjectId(product.brandId)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    product_dict = product.dict()
    if product_dict.get("image", "").startswith("data:image/"):
        product_dict["image"] = _save_base64_image(product_dict["image"])
    product_dict["brandName"] = brand["name"]
    product_dict["createdAt"] = datetime.utcnow()
    result = await db.products.insert_one(product_dict)
    product_dict["id"] = str(result.inserted_id)
    return Product(**product_dict)


@router.patch("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductUpdate, admin=Depends(get_admin_user)):
    update_dict = {k: v for k, v in product_data.dict().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    if update_dict.get("image", "").startswith("data:image/"):
        update_dict["image"] = _save_base64_image(update_dict["image"])
    if "brandId" in update_dict:
        brand = await db.brands.find_one({"_id": ObjectId(update_dict["brandId"])})
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        update_dict["brandName"] = brand["name"]
    result = await db.products.update_one({"_id": ObjectId(product_id)}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    return Product(id=str(product["_id"]), **{k: v for k, v in product.items() if k not in ("_id", "id")})


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, admin=Depends(get_admin_user)):
    result = await db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


@router.patch("/products/{product_id}/stock")
async def adjust_product_stock(product_id: str, adjustment: StockAdjustment, admin=Depends(get_admin_user)):
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    new_stock = product["stock"] + adjustment.adjustment
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative")
    await db.products.update_one({"_id": ObjectId(product_id)}, {"$set": {"stock": new_stock}})
    log_entry = {
        "productId": product_id,
        "productName": product["name"],
        "adjustment": adjustment.adjustment,
        "previousStock": product["stock"],
        "newStock": new_stock,
        "reason": adjustment.reason,
        "adminId": str(admin["_id"]),
        "timestamp": datetime.utcnow()
    }
    await db.inventory_logs.insert_one(log_entry)
    return {
        "message": "Stock adjusted successfully",
        "previousStock": product["stock"],
        "newStock": new_stock,
        "adjustment": adjustment.adjustment
    }


# ==================== UPLOAD ENDPOINT ====================

@router.post("/upload/product-image")
async def upload_product_image(file: UploadFile = File(...), admin=Depends(get_admin_user)):
    ext = Path(file.filename or "image.jpg").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOADS_DIR / filename
    filepath.write_bytes(data)
    return {"url": f"/api/uploads/products/{filename}"}


# ==================== REVIEW ENDPOINTS ====================

@router.get("/reviews/check/{product_id}")
async def check_can_review(product_id: str, user=Depends(get_current_user)):
    user_id = str(user["_id"])
    qualifying_order = await db.orders.find_one({
        "userId": user_id,
        "status": {"$in": ["Paid", "Ready for Pickup", "Completed"]},
        "items.productId": product_id,
    })
    if not qualifying_order:
        return {"canReview": False, "hasReviewed": False, "orderId": None}
    existing_review = await db.reviews.find_one({"productId": product_id, "userId": user_id})
    if existing_review:
        return {"canReview": False, "hasReviewed": True, "orderId": str(qualifying_order["_id"])}
    return {"canReview": True, "hasReviewed": False, "orderId": str(qualifying_order["_id"])}


@router.post("/reviews", response_model=ReviewResponse)
@limiter.limit("5/hour", key_func=get_user_id_or_ip)
async def create_review(request: Request, review_data: ReviewCreate, user=Depends(get_current_user)):
    user_id = str(user["_id"])
    if not (1 <= review_data.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    qualifying_order = await db.orders.find_one({
        "userId": user_id,
        "status": {"$in": ["Paid", "Ready for Pickup", "Completed"]},
        "items.productId": review_data.productId,
    })
    if not qualifying_order:
        raise HTTPException(status_code=403, detail="You can only review products you have purchased")
    existing = await db.reviews.find_one({"productId": review_data.productId, "userId": user_id})
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")
    doc = {
        "productId": review_data.productId,
        "userId": user_id,
        "orderId": review_data.orderId,
        "rating": review_data.rating,
        "comment": review_data.comment,
        "createdAt": datetime.utcnow().isoformat(),
        "userName": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
    }
    result = await db.reviews.insert_one(doc)
    return ReviewResponse(id=str(result.inserted_id), **{k: v for k, v in doc.items()})


@router.get("/reviews/product/{product_id}", response_model=List[ReviewResponse])
async def get_product_reviews(product_id: str):
    reviews = await db.reviews.find(
        {"productId": product_id, "isHidden": {"$ne": True}}
    ).sort("createdAt", -1).to_list(100)
    return [ReviewResponse(
        id=str(r["_id"]),
        isHidden=r.get("isHidden", False),
        **{k: v for k, v in r.items() if k not in ("_id", "isHidden")}
    ) for r in reviews]


@router.get("/categories")
async def get_categories():
    return [
        {"name": "Best Sellers", "value": "best-sellers"},
        {"name": "New Arrivals", "value": "new-arrivals"},
        {"name": "All Products", "value": "all"}
    ]
