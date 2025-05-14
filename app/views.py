from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from .models import (
    UserProfile,
    Timetable,
    Product,
    Notification,
    Post,
    Like,
    Comment,
    Savings,
    Expense,
)
from datetime import date


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if not all([username, password]):
            return render(
                request, "login.html", {"error": "Please fill in all fields."}
            )
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Successfully logged in.")
            return redirect("home")
        return render(request, "login.html", {"error": "Invalid username or password."})
    return render(request, "login.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        if not all([username, password1, password2]):
            return render(
                request, "signup.html", {"error": "Please fill in all fields."}
            )
        if password1 != password2:
            return render(request, "signup.html", {"error": "Passwords do not match."})
        if User.objects.filter(username=username).exists():
            return render(
                request, "signup.html", {"error": "Username is already taken."}
            )
        user = User.objects.create_user(username=username, password=password1)
        UserProfile.objects.create(user=user)
        Savings.objects.create(user=user)
        login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("home")
    return render(request, "signup.html")


@login_required
def logout_view(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")


@login_required
def home(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    # Calculate days until next exam
    today = date.today()
    timetables = Timetable.objects.filter(
        user=request.user, is_completed=False, exam_date__gte=today
    )
    days_until_exam = 0
    if timetables:
        days_until_exam = min(
            (t.exam_date - today).days for t in timetables if t.exam_date
        )
    # Calculate course completion percentage
    total_courses = Timetable.objects.filter(user=request.user).count()
    completed_courses = Timetable.objects.filter(
        user=request.user, is_completed=True
    ).count()
    course_completion = (
        (completed_courses / total_courses * 100) if total_courses else 0
    )
    # Calculate savings
    savings_obj = Savings.objects.get_or_create(user=request.user)[0]
    total_money = savings_obj.total_money
    expenses = Expense.objects.filter(user=request.user)
    total_expenses = sum(e.amount for e in expenses)
    savings = max(total_money - total_expenses, 0)
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "savings": round(savings, 2),
        "days_until_exam": days_until_exam,
        "course_completion": round(course_completion, 1),
        "notifications": notifications,
        "section": "dashboard",
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("home.html", context, request=request)
        return JsonResponse({"html": html})
    return render(request, "home.html", context)


@login_required
def profile_view(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    if request.method == "POST":
        user_profile.university_name = request.POST.get("university_name", "")
        if request.FILES.get("profile_picture"):
            user_profile.profile_picture = request.FILES["profile_picture"]
        user_profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "notifications": notifications,
        "section": "profile",
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("home.html", context, request=request)
        return JsonResponse({"html": html})
    return render(request, "home.html", context)


@login_required
def timetable_view(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    timetables = Timetable.objects.filter(user=request.user).order_by("day", "time")
    error = None
    if request.method == "POST":
        if "delete_id" in request.POST:
            timetable = get_object_or_404(
                Timetable, id=request.POST["delete_id"], user=request.user
            )
            timetable.delete()
            messages.success(request, "Timetable entry deleted.")
            return redirect("timetable")
        elif "toggle_completed_id" in request.POST:
            timetable = get_object_or_404(
                Timetable, id=request.POST["toggle_completed_id"], user=request.user
            )
            timetable.is_completed = request.POST.get("is_completed") == "on"
            timetable.save()
            messages.success(request, "Completion status updated.")
            return redirect("timetable")
        else:
            subject = request.POST.get("subject")
            day = request.POST.get("day")
            time = request.POST.get("time")
            exam_date = request.POST.get("exam_date") or None
            valid_days = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            if not all([subject, day, time]):
                error = "Subject, day, and time are required."
            elif day not in valid_days:
                error = "Invalid day selected."
            else:
                try:
                    Timetable.objects.create(
                        user=request.user,
                        subject=subject,
                        day=day,
                        time=time,
                        exam_date=exam_date,
                        is_completed=False,
                    )
                    messages.success(request, "Timetable entry added.")
                    return redirect("timetable")
                except ValidationError:
                    error = "Invalid time format. Use HH:MM."
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "timetables": timetables,
        "error": error,
        "notifications": notifications,
        "section": "timetable",
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("home.html", context, request=request)
        return JsonResponse({"html": html})
    return render(request, "home.html", context)


@login_required
def savings_view(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    savings_obj = Savings.objects.get_or_create(user=request.user)[0]
    expenses = Expense.objects.filter(user=request.user).order_by("-created_at")
    error = None
    total_money = savings_obj.total_money
    total_expenses = sum(e.amount for e in expenses)
    savings = max(total_money - total_expenses, 0)
    if request.method == "POST":
        if "total_money" in request.POST:
            try:
                total_money = float(request.POST.get("total_money"))
                if total_money < 0:
                    error = "Total money cannot be negative."
                else:
                    savings_obj.total_money = total_money
                    savings_obj.save()
                    messages.success(request, "Total money updated.")
                    return redirect("savings")
            except ValueError:
                error = "Invalid money amount."
        elif "expense_name" in request.POST:
            name = request.POST.get("expense_name")
            amount = request.POST.get("expense_amount")
            if not all([name, amount]):
                error = "Expense name and amount are required."
            else:
                try:
                    amount = float(amount)
                    if amount < 0:
                        error = "Expense amount cannot be negative."
                    else:
                        Expense.objects.create(
                            user=request.user,
                            savings=savings_obj,
                            name=name,
                            amount=amount,
                        )
                        messages.success(request, "Expense added.")
                        return redirect("savings")
                except ValueError:
                    error = "Invalid expense amount."
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "savings_obj": savings_obj,
        "expenses": expenses,
        "total_money": round(total_money, 2),
        "total_expenses": round(total_expenses, 2),
        "savings": round(savings, 2),
        "error": error,
        "notifications": notifications,
        "section": "savings",
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("home.html", context, request=request)
        return JsonResponse({"html": html})
    return render(request, "home.html", context)


@login_required
def shop_view(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    products = Product.objects.all().order_by("-created_at")
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        city = request.POST.get("city")
        country = request.POST.get("country")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        if not all([name, price, city, country, description]):
            messages.error(request, "All fields are required.")
        else:
            try:
                Product.objects.create(
                    seller=request.user,
                    name=name,
                    price=float(price),
                    city=city,
                    country=country,
                    description=description,
                    image=image,
                )
                messages.success(request, "Product posted successfully.")
                return redirect("shop")
            except ValueError:
                messages.error(request, "Invalid price format.")
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "products": products,
        "notifications": notifications,
        "section": "shop",
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("home.html", context, request=request)
        return JsonResponse({"html": html})
    return render(request, "home.html", context)


@login_required
def product_detail_view(request, product_id):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    product = get_object_or_404(Product, id=product_id)
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "product": product,
        "notifications": notifications,
        "section": "product_detail",
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("home.html", context, request=request)
        return JsonResponse({"html": html})
    return render(request, "home.html", context)


@login_required
def purchase_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.seller == request.user:
        messages.error(request, "You cannot purchase your own product.")
        return redirect("product_detail", product_id=product_id)
    if request.method == "POST":
        Notification.objects.create(
            recipient=product.seller,
            sender=request.user,
            product=product,
            message=f"{request.user.username} wants to purchase your product: {product.name}",
            status="pending",
        )
        messages.success(request, "Purchase request sent.")
        return redirect("product_detail", product_id=product_id)
    return redirect("shop")


@login_required
def explore_view(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    posts = Post.objects.all().order_by("-created_at")
    context = {
        "user": request.user,
        "user_profile": user_profile,
        "posts": posts,
        "notifications": notifications,
        "section": "explore",
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("home.html", context, request=request)
        return JsonResponse({"html": html})
    return render(request, "home.html", context)


@login_required
def create_post(request):
    if request.method == "POST":
        text = request.POST.get("text")
        image = request.FILES.get("image")
        if not text and not image:
            messages.error(request, "Post must have text or an image.")
            return redirect("explore")
        Post.objects.create(user=request.user, text=text or "", image=image)
        messages.success(request, "Post created successfully.")
        return redirect("explore")
    return redirect("explore")


@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse(
        {"success": True, "like_count": post.like_count(), "liked": liked}
    )


@login_required
def comment_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        text = request.POST.get("text")
        if not text:
            return JsonResponse(
                {"success": False, "error": "Comment cannot be empty."}, status=400
            )
        comment = Comment.objects.create(user=request.user, post=post, text=text)
        profile_picture = (
            request.user.userprofile.profile_picture.url
            if request.user.userprofile.profile_picture
            else "https://srmistvdp.edu.in/wp-content/uploads/2024/07/dummy-profile-pic-female-300n300.jpeg"
        )
        return JsonResponse(
            {
                "success": True,
                "comment_id": comment.id,
                "username": request.user.username,
                "text": comment.text,
                "user_profile_picture": profile_picture,
            }
        )
    return JsonResponse({"success": False, "error": "Invalid request."}, status=400)


@login_required
def handle_notification(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, recipient=request.user
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action in ["accept", "decline"]:
            notification.status = "accepted" if action == "accept" else "declined"
            notification.is_read = True
            notification.save()
            messages.success(request, f"Notification {notification.status}.")
            # Notify the sender
            Notification.objects.create(
                recipient=notification.sender,
                sender=request.user,
                product=notification.product,
                message=f"Your purchase request for {notification.product.name} was {notification.status} by {request.user.username}.",
                status=notification.status,
            )
        return redirect("home")
    return redirect("home")
