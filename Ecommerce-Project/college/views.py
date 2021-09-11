from django.shortcuts import render
from django.views.generic import View, TemplateView, CreateView, FormView, DetailView, ListView
from college.models import Product, Category, Cart, CartProduct, User, Customer, Order
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from college.forms import CheckoutForm,CustomerRegistrationForm,CustomerLoginForm
from django.db.models import Q


# Create your views here.

#We are Inheriting this class to Other Classes For Renaming Customer Name.
class EcomMixin(object):    
    def dispatch(self, request, *args, **kwargs):
        cart_id = request.session.get("cart_id") #Session Framework is used for Handeling Multiple Users Data--> 'cart_id' key used to Get Data of Html Element cart_id with Unique Session id
        if cart_id: #if cart_id has data then follow the process below
            cart_obj = Cart.objects.get(id=cart_id) #Storing Data In Cart_id key inside cart_obj variable
            if request.user.is_authenticated and request.user.customer:
                #if a user is Authenticated(login) and inside customer table
                cart_obj.customer = request.user.customer #Saving new Items inside cart_obj
                cart_obj.save()
        return super().dispatch(request, *args, **kwargs)




class HomeView(EcomMixin,TemplateView):
    template_name = "college/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['myname'] = "vivek" #All Products are Stored inside Vivek
        all_products = Product.objects.all().order_by("-id")

        paginator = Paginator(all_products, 8) #Limiting Products To 8 Products Per Page
        page_number = self.request.GET.get('page') #Current Page Number
        print(page_number)
        product_list = paginator.get_page(page_number)
        context['product_list'] = product_list
        return context



class AllProductsView(EcomMixin,TemplateView): #All Products in Table are Initially shown in page
    template_name = "college/allproducts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allcategories'] = Category.objects.all()
        return context

class ProductDetailView(EcomMixin,TemplateView): #Shows Product Details On Clicking Product At Home Page
    template_name = "college/product_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_slug = self.kwargs['slug']
        product = Product.objects.get(slug=url_slug)
        product.view_count += 1
        product.save()
        context['product'] = product
        return context




class AddToCartView(EcomMixin,TemplateView):
    template_name = "college/addtocart.html" #Cart html Page Object
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # get product id from requested url
        product_id = self.kwargs['pro_id'] #Store Product Ids inside product_id from **kwargs dict
        # Initiallizing Product_obj with Product_id key data
        product_obj = Product.objects.get(id=product_id)
        # check if cart contain item added inside in Page
        cart_id = self.request.session.get("cart_id", None)
        if cart_id: #if cart_id is not None  
            cart_obj = Cart.objects.get(id=cart_id)
            #Finding Products inside Product Table
            this_product_in_cart = cart_obj.cartproduct_set.filter(product=product_obj)

            # item already exists in cart
            if this_product_in_cart.exists():
                cartproduct = this_product_in_cart.last()

                cartproduct.quantity += 1
                cartproduct.subtotal += product_obj.selling_price
                cartproduct.save()
                cart_obj.total += product_obj.selling_price
                cart_obj.save()
            # new item is added in cart

            else:
                #if cart_id not exist then insert inside `cart_name` table
                cartproduct = CartProduct.objects.create(cart=cart_obj, product=product_obj, rate=product_obj.selling_price, quantity=1, subtotal=product_obj.selling_price)
                cart_obj.total += product_obj.selling_price
                cart_obj.save()

        else: #If same cart added again
            cart_obj = Cart.objects.create(total=0)
            self.request.session['cart_id'] = cart_obj.id
            cartproduct = CartProduct.objects.create(
                cart=cart_obj, product=product_obj, rate=product_obj.selling_price, quantity=1, subtotal=product_obj.selling_price)
            cart_obj.total += product_obj.selling_price
            cart_obj.save()

        return context


class MyCartView( EcomMixin,TemplateView): #Template For Cart
    template_name = "college/mycart.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_id = self.request.session.get("cart_id", None)
        if cart_id:
            cart = Cart.objects.get(id=cart_id)
        else:
            cart = None
        context['cart'] = cart
        return context


class ManageCartView(EcomMixin,View): #Management For Cart Items Addition and Removal
    def get(self, request, *args, **kwargs):
        cp_id = self.kwargs["cp_id"]  # Fetching Card Id
        action = request.GET.get("action")  # Getting Action From Html Page
        cp_obj = CartProduct.objects.get(id=cp_id)
        cart_obj = cp_obj.cart

        if action == "inc": #increase item Purchased
            cp_obj.quantity += 1
            cp_obj.subtotal += cp_obj.rate
            cp_obj.save()
            cart_obj.total += cp_obj.rate
            cart_obj.save()

        elif action == "dcr":  #decrease item Purchased
            cp_obj.quantity -= 1
            cp_obj.subtotal -= cp_obj.rate
            cp_obj.save()
            cart_obj.total -= cp_obj.rate
            cart_obj.save()
            if cp_obj.quantity == 0:
                cp_obj.delete()

        elif action == "rmv":  #remove item Purchased
            cart_obj.total -= cp_obj.subtotal
            cart_obj.save()
            cp_obj.delete()
        else:
            pass
        return redirect("mycart")



class EmptyCartView(EcomMixin,View):                   #To Empty the cart
    def get(self, request, *args, **kwargs):
        cart_id = request.session.get("cart_id", None) #If cart id not present Then Initiallize None
        if cart_id:                                    #If cart_id is Not None

            cart = Cart.objects.get(id=cart_id) #Storing Data of Select * from `cart` where cart_id=cart_id;   
            cart.cartproduct_set.all().delete() #Deleting all Products which are inside producy table
            cart.total = 0
            cart.save()
        return redirect("mycart")


class CheckoutView(EcomMixin,CreateView):
    template_name = "college/checkout.html"
    form_class = CheckoutForm           #importing checkoutform class from form.py file 
    success_url = reverse_lazy("home")  #Redirecting to the home page after cheackout successful
    #if the user is not login the he/she redirected to login page

    def dispatch(self, request, *args, **kwargs): #whenever user request then method will be exicuted
        print("hello iam dispatch method")
        if request.user.is_authenticated and request.user.customer:
            print("login user")                   #This message is printed when user is login
            pass
        else:
            print("not login user")
            return redirect("/college/login/?next=/checkout/") #redirect the user to login page if not login
        return super().dispatch(request, *args, **kwargs)




    def get_context_data(self, **kwargs): #inserting cart data to dict cart
        context = super().get_context_data(**kwargs)
        cart_id = self.request.session.get("cart_id", None)
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
        else:
            cart_obj = None
        context['cart'] = cart_obj
        return context


    def form_valid(self, form): 
        cart_id = self.request.session.get("cart_id") #cart_id contain session data
        if cart_id: #If cart_id contain data then following code execute
            cart_obj = Cart.objects.get(id=cart_id)  #Only the data whose cart_id match the Cart_id is accessed
            form.instance.cart = cart_obj #cart_obj data will be insert inserted to fields = ["ordered_by", "shipping_address", "mobile", "email", "payment_method"]
            form.instance.subtotal = cart_obj.total #insert the total amount to the subtotal field 
            form.instance.discount = 0 #discount field is 0 bydefayult
            form.instance.total = cart_obj.total #total field has same data as of total field contains 
            form.instance.order_status = "Order Received" #bydefault orderstatus is Order Recieved
            del self.request.session['cart_id'] #delete session after checkout the data

            

        else:
            return render("mycart") #redirects to mycart after database insertion completed
        return super().form_valid(form)





#payment getway lagane ka logik haiii
class KhaltiRequestView(View): #yaha se redirwct hohga khaltirequest.html page pe
    def get(self, request, *args, **kwargs):
        # o_id = request.GET.get("o_id") # khalti-request page par Your order amount is Rs.ke  bhi age order product ka total  likha aana chahiye
        # order = Order.objects.get(id=o_id) #bs is liye ye logik likha haii
        context = {
            # "order": order #Your order amount is Rs. 70000 aisa print hoga khalti-request page pe

        }
        return render(request, "college/khaltirequest.html", context)


#
# class KhaltiVerifyView(View):
#     def get(self, request, *args, **kwargs):
#         token = request.GET.get("token")
#         amount = request.GET.get("amount")
#         o_id = request.GET.get("order_id")
#         print(token, amount, o_id)
#
#         url = "https://khalti.com/api/v2/payment/verify/"
#         payload = {
#             "token": token,
#             "amount": amount
#         }
#         headers = {
#             "Authorization": "Key test_secret_key_f59e8b7d18b4499ca40f68195a846e9b"
#         }
#
#         order_obj = Order.objects.get(id=o_id)
#
#         response = requests.post(url, payload, headers=headers)
#         resp_dict = response.json()
#         if resp_dict.get("idx"):
#             success = True
#             order_obj.payment_completed = True
#             order_obj.save()
#         else:
#             success = False
#         data = {
#             "success": success
#         }
#         return JsonResponse(data)
#
#





class CustomerRegistrationView(CreateView):  #To Register a Custumer in Database CustomerRegistrationView class is used 
    template_name = "college/customerregistration.html"
    form_class = CustomerRegistrationForm
    success_url = reverse_lazy("home")

# To Insert Registration Form data inside Variables
    def form_valid(self, form):
        username = form.cleaned_data.get("username")            #username
        password = form.cleaned_data.get("password")            #password 
        email = form.cleaned_data.get("email")                  #Email
        user = User.objects.create_user(username, email, password) #Inserting Data to User Table
        form.instance.user = user #Inserts data inside customer table 
        login(self.request, user) #login process request done by user
        return super().form_valid(form)

class CustomerLogoutView(View): #class for logout functionality 
    def get(self, request):
        logout(request)
        return redirect("customerlogin")


class CustomerLoginView(FormView): #class for login functionality
    template_name = "college/customerlogin.html"
    form_class = CustomerLoginForm
    success_url = reverse_lazy("home")

    #form_valid method is a type of post method and is used in createview, formview and updateview 

    def form_valid(self, form):
        uname = form.cleaned_data.get("username")
        pword = form.cleaned_data["password"]
        usr = authenticate(username=uname, password=pword) #when user is authenticated(login)
        if usr is not None and Customer.objects.filter(user=usr).exists(): 
            login(self.request, usr) #For Login if not None
        else: #User is none when wrong id and password is given
            return render(self.request, self.template_name, {"form": self.form_class, "error": "Invalid credentials"})

        return super().form_valid(form)
    #
    # def get_success_url(self): #ja user checkout button pe click kar ke login kare or agar user login nhi haii
    #     #to sidha login button form pe ja raha haii lekin jab user login kar lega to wapis checkout page pe hi aana
    #     #chahiye uska code haii
    #     if "/college/next" in self.request.GET:
    #         next_url = self.request.GET.get("/college/next")
    #         return next_url
    #     else:
    #         return self.success_url




class CustomerProfileView(TemplateView):            #for profile page
    template_name = "college/customerprofile.html"

    def dispatch(self, request, *args, **kwargs): #if user is login then show his/her profile
        if request.user.is_authenticated and Customer.objects.filter(user=request.user).exists():
                       pass
        else: #if user is not login redirect to login page
            return redirect("/college/login/?next=/profile/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs): #get the data from costomers table
        context = super().get_context_data(**kwargs)
        customer = self.request.user.customer
        context['customer'] = customer 

        #showing data from orders table 
        orders = Order.objects.filter(cart__customer=customer).order_by("-id")
        context["orders"] = orders
        return context




class CustomerOrderDetailView(DetailView):
    template_name = "college/customerorderdetail.html"
    model = Order
    context_object_name = "ord_obj" #show profile data only if user is login

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and Customer.objects.filter(user=request.user).exists():
            order_id = self.kwargs["pk"]
            order = Order.objects.get(id=order_id) #fetch id from urls
            if request.user.customer != order.cart.customer: #if user is customer
                return redirect("customerprofile") #redirect to customer profile if login
        else: #else redirect to profile 
            return redirect("/college/login/?next=/profile/")
        return super().dispatch(request, *args, **kwargs)



class SearchView(TemplateView):
    template_name = "college/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kw = self.request.GET.get("keyword") #code for search field
        results = Product.objects.filter(Q(title__icontains=kw) | Q(description__icontains=kw) | Q(return_policy__icontains=kw))
        print(results)
        context["results"] = results
        return context




class PasswordForgotView(TemplateView):
    template_name = "college/forgotpassword.html"





