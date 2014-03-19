# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from forms import UserForm, TeamForm, RatingForm, DemoForm
from models import Demo, Category, Team, Rating, Rater
from django.contrib.auth.decorators import login_required


def get_rater(user):
    if user.is_anonymous():
        return None
    r = Rater.objects.filter(user=user)
    if len(r) == 1:
        return r[0]
    else:
        return None


def get_team(user):
    if user.is_anonymous():
        # or we could check if the user id is None
        return None
    t = Team.objects.filter(user=user)
    if len(t)==1:
        return t[0]
    else:
        return None


def add_isteam_to_context_dict(context_dict, team):
    if team:
        context_dict['isteam'] = True
        context_dict['currteam'] = team
    else:
        context_dict['isteam'] = False
        context_dict['currteam'] = None

def add_hero_cats_to_context_dict(context_dict,catid=None):
    if catid:
        demos = Demo.objects.filter(category=catid)
    else:
        demos = Demo.objects.all()

    demo_list = sorted(demos, key = lambda d: d.rating_average, reverse=True)
    if len(demo_list) >=1:
        hero = demo_list[0]
        demo_list = demo_list[1:]
        context_dict['hero'] = hero
        context_dict['demos'] = demo_list
    else:
        context_dict['hero'] = None
        context_dict['demos'] = None



def index(request):
    # Request the context of the request.
    # The context contains information such as the client's machine details, for example.
    context = RequestContext(request)
    context_dict = { }

    add_hero_cats_to_context_dict(context_dict)
    t = get_team(request.user)
    add_isteam_to_context_dict(context_dict, t)
    return render_to_response('showcase/index.html', context_dict, context)


def category_show(request, catid):
    context = RequestContext(request)
    context_dict = { }
    add_hero_cats_to_context_dict(context_dict, catid)

    #demo_list = Demo.objects.filter(category=catid)
    cat_list = Category.objects.all()
    cat = Category.objects.get(id=catid)

    context_dict['cats']=cat_list
    context_dict['catid']=catid
    context_dict['cat']=cat

    t = get_team(request.user)
    add_isteam_to_context_dict(context_dict, t)

    return render_to_response('showcase/index.html', context_dict, context)


def demo_show(request, demoid):
    context = RequestContext(request)
    #TODO(leifos): add in error handlding and checking, handle gracefully
    demo = Demo.objects.get(id=demoid)
    team = demo.team
    ratings = Rating.objects.filter(demo=demo).order_by('-score')
    rater = get_rater(request.user)
    can_rate = False
    if rater:
        can_rate = True
    context_dict = {'team': team, 'demo': demo, 'ratings':ratings, 'can_rate': can_rate }
    t = get_team(request.user)
    add_isteam_to_context_dict(context_dict, t)

    if can_rate:
        rate_form = RatingForm()
        context_dict['rate_form'] = rate_form


    return render_to_response('showcase/demo.html', context_dict, context)


@login_required
def demo_rate(request, demoid):
    context = RequestContext(request)
    context_dict ={}
    t = get_team(request.user)
    add_isteam_to_context_dict(context_dict, t)

    rater = get_rater(request.user)

    if rater:
        if request.method == 'POST':
            rating_form = RatingForm(data=request.POST)
            if rating_form.is_valid():
                demo = Demo.objects.get(id=demoid)

                # check if the rater has already rated this app, if so, remove this entry and replace with new rating
                rating_check = Rating.objects.filter(rater=rater,demo=demo).count()
                if rating_check == 1:
                    past_rating = Rating.objects.get(rater=rater,demo=demo)
                    demo.rating_count = demo.rating_count - 1
                    demo.rating_sum = demo.rating_sum - past_rating.score
                    past_rating.delete()
                    demo.save()

                rating = rating_form.save(commit=False)
                rating.rater = rater
                rating.demo = demo
                rating.save()
                demo.rating_count = demo.rating_count + 1
                demo.rating_sum = demo.rating_sum + rating.score
                demo.save()

                return HttpResponseRedirect('/showcase/demo/show/'+str(demoid)+'/')
            else:
                print rating_form.errors
        else:
            rating_form = RatingForm()

            context_dict['rating_form']=rating_form
            return render_to_response(
            'showcase/demo.html',
            context_dict,
            context)

    return HttpResponseRedirect('/showcase/demo/show/'+str(demoid)+'/')


@login_required
def demo_add(request):
    context = RequestContext(request)
    context_dict ={}
    t = get_team(request.user)
    add_isteam_to_context_dict(context_dict, t)

    added = False
    t = get_team(request.user)
    if t:
        if request.method == 'POST':
            demo_form = DemoForm(data=request.POST)
            if demo_form.is_valid():
                demo = demo_form.save(commit=False)
                demo.team = t
                if 'screenshot' in request.FILES:
                    demo.logo = request.FILES['screenshot']

                demo.save()
                added = True
                return HttpResponseRedirect('/showcase/team/'+str(t.id)+'/')
            else:
                print demo_form.errors
        else:
            demo_form = DemoForm()

        # Render the template depending on the context.
        context_dict['demo_form'] = demo_form
        context_dict['added'] = added
        return render_to_response(
            'showcase/demo_add.html',
                context_dict, context)
    else:
        return HttpResponse('You need to be a team to add a demo.')

@login_required
def demo_edit(request, demoid=None):
    """
    Thanks to: http://wiki.ddenis.com/index.php?title=Django,_add_and_edit_object_together_in_the_same_form
    """
    context = RequestContext(request)
    t = get_team(request.user)
    context_dict ={}
    add_isteam_to_context_dict(context_dict, t)

    edit = False
    if t:
        if demoid:
            demo = get_object_or_404(Demo, pk=demoid)
            edit = True
            print demo, demo.id, demo.url
            if demo.team.user != request.user:
                return HttpResponseForbidden()
        else:
            demo = Demo(team=t)
        #Could use this instead -> if request.POST:
        if request.method == 'POST':
            demo_form = DemoForm(request.POST, request.FILES, instance=demo)
            if demo_form.is_valid():
                if 'screenshot' in request.FILES:
                    demo.logo = request.FILES['screenshot']
                demo_form.save()
                return HttpResponseRedirect('/showcase/team/'+str(t.id)+'/')
            else:
                print demo_form.errors
        else:
            demo_form = DemoForm(instance=demo)

        # Render the template depending on the context.
        return render_to_response(
            'showcase/demo_add.html',
            {'demo_form': demo_form, 'demoid':demoid,'edit':edit},
            context)
    else:
        return HttpResponse('You need to be a team to add or edit a demo.')



def team_show(request, teamid):
    context = RequestContext(request)
    context_dict = {}
    currteam = get_team(request.user)

    team = Team.objects.get(id=teamid)
    myteam = False
    if currteam:
        if currteam.id == team.id:
            myteam = True

    demo_list = Demo.objects.filter(team=team)

    context_dict = {'team': team, 'demos': demo_list, 'myteam': myteam}
    add_isteam_to_context_dict(context_dict, currteam)
    print context_dict
    return render_to_response('showcase/team.html', context_dict, context)



def register(request):
    context = RequestContext(request)
    #team = Team.objects.get(id=int(teamid))
    #demo_list = Demo.objects.filter(team=team)
    #context_dict = {'team': team, 'demos': demo_list}
    context_dict = {}
    return render_to_response('showcase/register.html', context_dict, context)


def register_rater(request):
    context = RequestContext(request)
    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        if user_form.is_valid():
            user = user_form.save()
            password = user.password
            user.set_password(user.password)
            user.save()
            r = Rater(user=user, active=True)
            r.save()
            registered = True
            user = authenticate(username=user.username, password=password)
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)
            return HttpResponseRedirect('/showcase/')
        else:
            print user_form.errors
    else:
        user_form = UserForm()

    # Render the template depending on the context.
    return render_to_response(
            'showcase/rater_registration.html',
            {'user_form': user_form, 'registered': registered},
            context)



def register_team(request):
    context = RequestContext(request)
    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        team_form = TeamForm(request.POST, request.FILES)
        if user_form.is_valid():
            if team_form.is_valid():
                user = user_form.save()
                # do i need these two lines anymore? Django 1.5, i think, handles this automatically now.
                password = user.password
                user.set_password(password)
                user.save()
                t = team_form.save(commit=False)
                t.user = user
                t.save()
                registered = True
                user = authenticate(username=user.username, password=password)
                login(request, user)
                return HttpResponseRedirect('/showcase/team/'+str(t.id)+'/')
        else:
            print user_form.errors, team_form.errors
    else:
        user_form = UserForm()
        team_form = TeamForm()

    # Render the template depending on the context.
    return render_to_response(
            'showcase/team_registration.html',
            {'user_form': user_form, 'team_form':team_form, 'registered': registered},
            context)


def user_login(request):
    context = RequestContext(request)
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/showcase/')
            else:
                return HttpResponse("Your ShowCase account is disabled.")
        else:
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Invalid login details supplied.")

    else:
        return render_to_response('showcase/login.html', {}, context)



# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/showcase/')


def ack(request):
    context = RequestContext(request)
    context_dict = { }
    add_hero_cats_to_context_dict(context_dict)
    t = get_team(request.user)
    add_isteam_to_context_dict(context_dict, t)
    return render_to_response('showcase/ack.html', context_dict, context)
