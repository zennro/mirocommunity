import mock
import datetime
import urllib2

from django.contrib.auth.models import User
from django.core.files import File
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.test.utils import override_settings
from vidscraper.videos import (Video as VidscraperVideo,
                               VideoFile as VidscraperVideoFile)

from localtv.models import Video, SiteSettings
from localtv.signals import submit_finished
from localtv.submit_video import forms
from localtv.submit_video.views import (_has_submit_permissions,
                                        SubmitURLView,
                                        SubmitVideoView)
from localtv.tests.base import BaseTestCase
from localtv.utils import get_or_create_tags


class SubmitPermissionsTestCase(BaseTestCase):
    """
    Test case for submit permissions.

    """
    fixtures = ['users']
    def setUp(self):
        BaseTestCase.setUp(self)
        url = reverse('localtv_submit_video')
        self.site_settings = SiteSettings.objects.get()
        self.anonymous_request = self.factory.get(url)
        self.user_request = self.factory.get(
            url, user=User.objects.get(username='user'))
        self.admin_request = self.factory.get(
            url, user=User.objects.get(username='admin'))

    def test_all_permitted(self):
        """
        If login is not required, all requests should pass the permissions
        check.

        """
        self.site_settings.submission_requires_login = False
        self.site_settings.save()
        self.assertTrue(_has_submit_permissions(self.anonymous_request))
        self.assertTrue(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))

    def test_login_required(self):
        """
        If login is required and a submit button is available, all logged-in
        requests should pass the permissions check.

        """
        self.site_settings.submission_requires_login = True
        self.site_settings.display_submit_button = True
        self.site_settings.save()
        self.assertFalse(_has_submit_permissions(self.anonymous_request))
        self.assertTrue(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))

    def test_admin_required(self):
        """
        If login is required and no submit button is displayed, only admin
        requests should pass the permissions check.

        """
        self.site_settings.submission_requires_login = True
        self.site_settings.display_submit_button = False
        self.site_settings.save()
        self.assertFalse(_has_submit_permissions(self.anonymous_request))
        self.assertFalse(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))


class SubmitURLViewTestCase(BaseTestCase):
    def test_GET_submission(self):
        """
        Form data should be captured from the GET parameters.

        """
        view = SubmitURLView()
        url = "%s?%s" % (reverse('localtv_submit_video'),
                         "url=http://google.com")
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())
        self.assertEqual(form.data, view.request.GET)

    def test_form_valid__scraped__embed(self):
        """
        Checks that, if the form represents a scraped video with embed code,
        the success_url is the url of the scraped_video view, and that the
        session data contains the scraped video as 'video' and the video's
        url as 'url'.

        """
        scraped_url = reverse('localtv_submit_scraped_video')
        view = SubmitURLView(scraped_url=scraped_url)
        video_url = "http://google.com"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (scraped_url,
                                          view.request.GET.urlencode())
        form = view.get_form(view.get_form_class())

        video = VidscraperVideo(video_url)
        video.embed_code = "blink"
        form.video_cache = video
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

    def test_form_valid__scraped__file_url(self):
        """
        Checks that, if the form represents a scraped video with a file_url,
        the success_url is the url of the scraped_video view, and that the
        session data contains the scraped video as 'video' and the video's
        url as 'url'.

        """
        scraped_url = reverse('localtv_submit_scraped_video')
        view = SubmitURLView(scraped_url=scraped_url)
        video_url = "http://google.com"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (scraped_url,
                                          view.request.GET.urlencode())
        form = view.get_form(view.get_form_class())

        video = VidscraperVideo(video_url)
        video.embed_code = None
        video.files = [VidscraperVideoFile(url="blink")]
        form.video_cache = video
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)


    def test_form_valid__directlink(self):
        """
        Checks that, if the form represents a direct link to a video file, the
        success_url is the url of the direct_link view, and that the session
        data contains the video (or ``None``) as 'video' and the video's url
        as 'url'.

        NOTE:: Direct link videos will probably not actually result in the
        creation of VidscraperVideo instances; this is tested only to maintain
        the exact behavior which previously existed.

        """
        direct_url = reverse('localtv_submit_directlink_video')
        view = SubmitURLView(direct_url=direct_url)
        video_url = "http://google.com/file.mov"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (direct_url,
                                          view.request.GET.urlencode())
        form = view.get_form(view.get_form_class())

        # Option one: No video, but a video file url.
        form.video_cache = None
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': None, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

        # Option two: A video missing embed_code and file_url data, but a video
        # file url.
        video = VidscraperVideo(video_url)
        form.video_cache = video
        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)


    def test_form_valid__embedrequest(self):
        """
        Checks that, if the form represents an embedrequest video - i.e. a video
        that vidscraper can't scrape and which doesn't look like a direct link -
        the success_url is set to the url of the embedrequest view, and that the
        session data contains the scraped video (or ``None``) as 'video' and the
        video's url as 'url'.

        """
        embed_url = reverse('localtv_submit_embedrequest_video')
        view = SubmitURLView(embed_url=embed_url)
        video_url = 'http://google.com'
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (embed_url,
                                          view.request.GET.urlencode())
        form = view.get_form(view.get_form_class())

        # Option 1: no video
        form.video_cache = None
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': None, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

        # Option two: video missing embed & file_url
        video = VidscraperVideo(video_url)
        form.video_cache = video
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

        # Option three: video with expiring file_url.
        video.file_url = 'hola'
        video.file_url_expires = datetime.datetime.now() + datetime.timedelta(1)

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

    @mock.patch('vidscraper.auto_scrape',
                mock.Mock(side_effect=urllib2.URLError('foo')))
    def test_form_valid__vidscraper_urlerror(self):
        """
        If ``vidscraper.auto_scrape()`` raises a URLError, we should not have a
        video_cache and the user should be redirected to the embedrequest page.
        """
        embed_url = reverse('localtv_submit_embedrequest_video')
        view = SubmitURLView(embed_url=embed_url)
        video_url = 'http://google.com/'
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (embed_url,
                                          view.request.GET.urlencode())
        form = view.get_form(view.get_form_class())

        self.assertTrue(form.is_valid())

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': None, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)


    def test_get_context_data(self):
        """
        Makes sure that ``was_duplicate`` and ``video`` are context variables
        taken from attributes on the form instance. The setting of those
        attributes is tested in the form unit tests.

        """
        video = self.create_video()
        url = video.website_url or video.file_url or video.guid
        view = SubmitURLView()
        form = view.form_class(data={'url': url})

        form.was_duplicate = True
        form.duplicate_video = video
        context = view.get_context_data(form=form)
        self.assertTrue('was_duplicate' in context)
        self.assertTrue('video' in context)
        self.assertEqual(context['was_duplicate'], True)
        self.assertEqual(context['video'], video)


@override_settings(LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL=True)
class SubmitVideoViewTestCase(BaseTestCase):
    def test_requires_session_data(self):
        # This differs from the functional testing in that it tests the view
        # directly. The inputs given can only result in a 302 response or a 200
        # response, depending on whether there is correct session data or not.
        view = SubmitVideoView(form_class=forms.SubmitVideoFormBase,
                               submit_video_url='http://google.com/')
        request = self.factory.get('/')
        response = view.dispatch(request)
        self.assertEqual(response.status_code, 302)

        request.session[view.get_session_key()] = {
            'url': 'http://google.com',
            'video': VidscraperVideo('http://google.com/')}
        response = view.dispatch(request)
        self.assertEqual(response.status_code, 200)

    def test_get_initial_tags(self):
        """
        Tests that tags are in the initial data only if tags are defined on the
        video, and that the tags in the expected format - at the moment, this
        is the return value of get_or_create_tags(tags).

        """
        view = SubmitVideoView()
        view.video = VidscraperVideo('http://google.com')
        initial = view.get_initial()
        self.assertFalse('tags' in initial)

        tags = ['hello', 'goodbye']
        view.video.tags = tags
        initial = view.get_initial()
        self.assertTrue('tags' in initial)
        # This is perhaps not the best way to test this.
        self.assertEqual(initial['tags'], get_or_create_tags(tags))

    def test_form_valid(self):
        """
        Tests that when the form_valid method is run, the session information
        is cleared, and the submit_finished signal is sent.

        """
        view = SubmitVideoView(form_class=forms.SubmitVideoFormBase,
                               form_fields=('tags', 'contact', 'notes',),
                               thanks_url_name='localtv_submit_thanks')
        view.request = self.factory.get('/')
        view.object = Video()
        view.url = u'http://google.com/'
        view.video = VidscraperVideo(view.url)
        view.video.embed_code = 'Test Code'
        view.request.session[view.get_session_key()] = {
            'url': view.url,
            'video': view.video
        }

        submit_dict = {'hit': False}
        def test_submit_finished(sender, **kwargs):
            submit_dict['hit'] = True
        submit_finished.connect(test_submit_finished)
        form = view.get_form_class()(data={'url': view.url,
                                           'name': 'Test Video',
                                           'embed_code': 'Test Code',
                                           'contact': 'test@test.com'},
                                     **view.get_form_kwargs())
        self.assertTrue(form.is_valid(), form.errors.items())
        self.assertTrue(view.form_valid(form))

        self.assertEqual(submit_dict['hit'], True)
        self.assertFalse(view.get_session_key() in view.request.session)
        submit_finished.disconnect(test_submit_finished)

    def test_compatible_context(self):
        """
        Tests that the get_context_data method supplies a backwards-compatible
        "data" context variable in addition to adding the form and video to the
        context.

        """
        view = SubmitVideoView(form_class=forms.SubmitVideoFormBase)
        view.request = self.factory.get('/')
        view.request.session[view.get_session_key()] = {
            'url': '',
            'video': VidscraperVideo('')
        }
        view.object = self.create_video()
        view.url = (view.object.website_url or view.object.file_url)
        view.video = VidscraperVideo(view.url)
        form = view.get_form(view.get_form_class())

        context_data = view.get_context_data(form=form)
        self.assertEqual(context_data.get('video'), view.object)
        self.assertIsInstance(context_data.get('form'), view.form_class)
        self.assertTrue('data' in context_data)
        self.assertEqual(set(context_data['data']),
                         set(['link', 'publish_date', 'tags', 'title',
                              'description', 'thumbnail_url', 'user',
                              'user_url']))

    def test_get_object(self):
        """
        Tests that the view's get_object method returns a Video instance,
        populated with data from a vidscraper video if available.

        """
        view = SubmitVideoView()
        view.video = None
        obj = view.get_object()
        self.assertIsInstance(obj, Video)
        self.assertEqual(obj.name, '')
        self.assertEqual(obj.embed_code, '')

        view.video = VidscraperVideo('')
        view.video.title = 'Title'
        view.video.embed_code = 'embed_code'
        obj = view.get_object()
        self.assertIsInstance(view.get_object(), Video)
        self.assertEqual(obj.name, 'Title')
        self.assertEqual(obj.embed_code, 'embed_code')


class SubmitVideoFormBaseTestCase(BaseTestCase):
    def setUp(self):

        BaseTestCase.setUp(self)
        self.form_class = modelform_factory(Video, forms.SubmitVideoFormBase)

    def test_sanitize_description(self):
        """
        Tests that the video description is sanitized, and that in
        particular, img tags are removed.

        """
        request = self.factory.get('/')
        form = self.form_class(request, 'http://google.com')
        form.cleaned_data = {'description': "<img src='http://www.google.com/' alt='this should be stripped' />"}
        self.assertEqual(form.clean_description(), '')


class ThumbnailSubmitVideoFormTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.form_class = modelform_factory(Video,
                                            forms.ThumbnailSubmitVideoForm)

    def test_thumbnail_file_override(self):
        """
        Tests that if a thumbnail_file is given to the form, it will override
        the thumbnail_url.

        """
        request = self.factory.get('/')
        form = self.form_class(
            request, 'http://google.com',
            data={
                'url': 'http://google.com',
                'name': 'Test Name',
                'embed_code': 'Test Embed',
                'thumbnail_url': 'http://google.com'},
            files={'thumbnail_file': File(file(self._data_file('logo.png')))})

        self.assertTrue(form.is_valid(), form.errors)
        video = form.save()
        self.assertTrue(video.thumbnail)
        self.assertEqual(video.thumbnail_url, '')
