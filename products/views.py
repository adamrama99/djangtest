from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, DocumentationRequest
from .forms import ProductForm, DocumentationRequestForm

def product_list(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "products/list.html", {"products": products})

def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("product_list")
    return render(request, "products/forms.html", {"form": form, "title": "Create Product"})

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("product_list")
    return render(request, "products/forms.html", {"form": form, "title": "Edit Product"})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect("product_list")
    return render(request, "products/delete.html", {"product": product})

def dashboard(request):
    # Focus only on documentation requests
    requests = DocumentationRequest.objects.all()
    total_requests = requests.count()
    
    return render(request, "products/dashboard.html", {
        "total_requests": total_requests,
    })

# --- Documentation Request Views ---

def doc_request_list(request):
    requests = DocumentationRequest.objects.all().order_by("-id")
    return render(request, "products/request_list.html", {"requests": requests})

def doc_request_create(request):
    form = DocumentationRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("doc_request_list")
    return render(request, "products/request_form.html", {"form": form, "title": "Create Documentation Request"})

def doc_request_detail(request, pk):
    doc_request = get_object_or_404(DocumentationRequest, pk=pk)
    return render(request, "products/request_detail.html", {"request": doc_request})

def doc_request_delete(request, pk):
    doc_request = get_object_or_404(DocumentationRequest, pk=pk)
    if request.method == "POST":
        doc_request.delete()
        return redirect("doc_request_list")
    return render(request, "products/request_delete.html", {"request_obj": doc_request})