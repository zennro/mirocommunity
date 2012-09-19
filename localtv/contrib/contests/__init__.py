# Trigger some adjustments to core registries.
from localtv import context_processors
from localtv.contrib.contests.api import v1
from localtv.views import VideoView


context_processors.BROWSE_NAVIGATION_MODULES.append(
									'localtv/_modules/browse/contests.html')
VideoView.sidebar_modules.insert(0, 'localtv/_modules/contests.html')
