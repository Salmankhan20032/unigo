from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("home/", views.home, name="home"),
    path("profile/", views.profile_view, name="profile"),
    path("timetable/", views.timetable_view, name="timetable"),
    path("savings/", views.savings_view, name="savings"),
    path("shop/", views.shop_view, name="shop"),
    path("product/<int:product_id>/", views.product_detail_view, name="product_detail"),
    path("purchase/<int:product_id>/", views.purchase_product, name="purchase_product"),
    path(
        "notification/<int:notification_id>/",
        views.handle_notification,
        name="handle_notification",
    ),
    path("explore/", views.explore_view, name="explore"),
    path("post/create/", views.create_post, name="create_post"),
    path("like_post/<int:post_id>/", views.like_post, name="like_post"),
    path("comment_post/<int:post_id>/", views.comment_post, name="comment_post"),
]
