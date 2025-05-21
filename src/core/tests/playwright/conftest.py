from datetime import datetime, timedelta
import os
import random
import pytest
import subprocess
from playwright.sync_api import Browser


@pytest.fixture(scope="session")
def build_gui():
    try:
        if os.getenv("E2E_TEST_GUI_REBUILD") == "true" or not os.path.isdir("../gui/dist"):
            if not os.path.isdir("../gui/node_modules"):
                print("Building node_modules")
                print(os.path.isdir("../gui/node_modules"))
                result = subprocess.call(["pnpm", "install"], cwd="../gui")
                assert result == 0, f"Install failed with status code: {result}"

            print("Building GUI")
            env = os.environ.copy()
            env["VITE_TARANIS_CONFIG_JSON"] = "/config.json"
            result = subprocess.call(
                ["pnpm", "run", "build"],
                cwd="../gui",
                env=env,
            )
            assert result == 0, f"Build failed with status code: {result}"
        else:
            print("Reusing existing dist folder, delete it to force a rebuild")
    except Exception as e:
        pytest.fail(str(e))


@pytest.fixture(scope="class")
def e2e_ci(request):
    request.cls.ci_run = request.config.getoption("--e2e-ci") == "e2e_ci"
    request.cls.wait_duration = float(request.config.getoption("--highlight-delay"))

    if request.cls.ci_run:
        print("Running in CI mode")


@pytest.fixture(scope="session")
def e2e_server(app, live_server, stories, build_gui):
    import core.api as core_api

    core_api.frontend.initialize(app)
    live_server.app = app
    live_server.start()
    yield live_server


@pytest.fixture(scope="session")
def pic_prefix(request):
    yield ""


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, browser_type_launch_args, request):
    browser_type_launch_args["args"] = ["--window-size=1964,1211"]

    if request.config.getoption("--record-video"):
        return {
            **browser_context_args,
            "record_video_dir": "tests/playwright/videos",
            "no_viewport": True,
            "record_video_size": {"width": 1920, "height": 1080},
        }
    return {**browser_context_args, "no_viewport": True}


@pytest.fixture(scope="session")
def taranis_frontend(request, e2e_server, browser_context_args, browser: Browser):
    context = browser.new_context(**browser_context_args)
    # Drop timeout from 30s to 10s
    timeout = int(request.config.getoption("--e2e-timeout"))
    context.set_default_timeout(timeout)
    if request.config.getoption("--e2e-ci") == "e2e_ci":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()
    page.goto(e2e_server.url())
    yield page
    if request.config.getoption("--e2e-ci") == "e2e_ci":
        context.tracing.stop(path="taranis_ai_core_trace.zip")


@pytest.fixture(scope="session")
def e2e_setup(app):
    with app.app_context():
        from core.model.user import User

        current_user = User.find_by_name("admin")
        if not current_user:
            pytest.fail("Admin user not found")
        user_profile = {
            "dark_theme": False,
            "hotkeys": {},
            "split_view": False,
            "compact_view": False,
            "show_charts": False,
            "infinite_scroll": False,
            "end_of_shift": {"hours": 18, "minutes": 0},
            "language": "en",
        }
        User.update_profile(current_user, user_profile)


@pytest.fixture(scope="session")
def fake_source(app, e2e_setup):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        source_data = {
            "id": "99",
            "description": "This is a test source",
            "name": "Test Source",
            "parameters": [
                {"FEED_URL": "https://url/feed.xml"},
            ],
            "type": "rss_collector",
        }
        OSINTSource.add(source_data)

        yield source_data["id"]


def random_timestamp_last_5_days() -> str:
    now = datetime.now()
    start_time = now - timedelta(days=5)
    return (start_time + timedelta(seconds=random.randint(0, int((now - start_time).total_seconds())))).isoformat()


def random_timestamp_last_shift() -> str:
    ### Add a random timestamp between now and yesterday 18:00
    now = datetime.now()
    start_time = now - timedelta(days=1)
    start_time = start_time.replace(hour=18, minute=0, second=0, microsecond=0)
    return (start_time + timedelta(seconds=random.randint(0, int((now - start_time).total_seconds())))).isoformat()


@pytest.fixture(scope="session")
def stories(app, news_items_list):
    from core.model.story import Story
    from core.model.user import User

    def _renew_story_timestamps():
        for item in news_items_list[:-5]:
            new_time = random_timestamp_last_shift()
            item.update({"published": new_time})
            item.update({"collected": new_time})
        for item in news_items_list[-5:]:
            new_time = random_timestamp_last_5_days()
            item.update({"published": new_time})
            item.update({"collected": new_time})

    _renew_story_timestamps()

    with app.app_context():
        story_ids = Story.add_news_items(news_items_list)[0].get("story_ids")
        user = User
        user.id = 1
        if not story_ids:
            raise ValueError("Error getting stories")
        Story.update(story_ids[0], data={"important": True}, user=user)
        Story.update(story_ids[8], data={"important": True}, user=user)
        Story.update(story_ids[13], data={"important": True}, user=user)
        Story.update(story_ids[17], data={"important": True}, user=user)
        Story.update(story_ids[21], data={"important": True}, user=user)
        story_groups = [
            [story_ids[0], story_ids[1], story_ids[2], story_ids[3], story_ids[4], story_ids[5], story_ids[6], story_ids[7]],
            [story_ids[8], story_ids[9], story_ids[10], story_ids[11], story_ids[12]],
            [story_ids[13], story_ids[14], story_ids[15], story_ids[16]],
            [story_ids[17], story_ids[18], story_ids[19], story_ids[20]],
            [story_ids[21], story_ids[22], story_ids[23]],
        ]
        Story.group_multiple_stories(story_groups)

        yield story_ids


@pytest.fixture(scope="session")
def story_news_items(app, stories):
    from core.model.story import Story

    story_news_items_dict = {}
    with app.app_context():
        for story_id in stories:
            if story := Story.get(story_id):
                story_news_items_dict[story_id] = story.news_items
            else:
                story_news_items_dict[story_id] = []

    yield story_news_items_dict


@pytest.fixture(scope="session")
def stories_date_descending(app, stories):
    from core.model.story import Story

    with app.app_context():
        creation_timestamps = []
        for story_id in stories:
            if s := Story.get(story_id):
                creation_timestamps.append(s.created)
            else:
                creation_timestamps.append(datetime.fromtimestamp(0))
        story_ids = [story_id for story_id, _ in sorted(zip(stories, creation_timestamps), key=lambda x: x[1], reverse=True)]
    yield story_ids


@pytest.fixture(scope="session")
def stories_date_descending_not_important(app, stories_date_descending):
    from core.model.story import Story

    with app.app_context():
        story_ids = []
        for story_id in stories_date_descending:
            if s := Story.get(story_id):
                if not s.important:
                    story_ids.append(story_id)
    yield story_ids


@pytest.fixture(scope="session")
def stories_date_descending_important(app, stories_date_descending):
    from core.model.story import Story

    with app.app_context():
        story_ids = []
        for story_id in stories_date_descending:
            if s := Story.get(story_id):
                if s.important:
                    story_ids.append(story_id)
    yield story_ids


@pytest.fixture(scope="session")
def stories_relevance_descending(app, stories):
    from core.model.story import Story

    with app.app_context():
        relevances = []
        for story_id in stories:
            if s := Story.get(story_id):
                relevances.append(s.relevance)
            else:
                relevances.append(0)
        story_ids = [story_id for story_id, _ in sorted(zip(stories, relevances), key=lambda x: x[1], reverse=True)]
    yield story_ids


@pytest.fixture(scope="session")
def news_items_list(app, fake_source):
    yield [
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk21",
            "content": "APT81 targets national research labs to steal genetic engineering data.",
            "source": "https://www.researchlabsecurity.com/RSSNewsfeed.xml",
            "title": "Genetic Engineering Data Theft by APT81",
            "author": "Irene Thompson",
            "collected": "2024-05-19T00:00:14.086285",
            "hash": "t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5",
            "review": "",
            "link": "https://www.geneticresearchsecurity.com/apt81-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-19T00:35:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk14",
            "content": "APT74 involved in sabotaging smart city projects across Europe.",
            "source": "https://www.smartcitysecuritynews.com/RSSNewsfeed.xml",
            "title": "Smart City Sabotage by APT74 in Europe",
            "author": "Bethany White",
            "collected": "2024-04-12T07:10:30.123456",
            "hash": "m7n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8",
            "review": "",
            "link": "https://www.smartcityupdate.com/apt74-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-04-12T08:45:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk15",
            "content": "APT75 uses sophisticated cyber attacks to manipulate international media outlets.",
            "source": "https://www.mediasecurityupdates.com/RSSNewsfeed.xml",
            "title": "International Media Manipulation by APT75",
            "author": "Charles Lee",
            "collected": "2024-05-13T06:00:14.086285",
            "hash": "n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9",
            "review": "",
            "link": "https://www.mediasecurityfocus.com/apt75-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-13T06:35:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk16",
            "content": "APT76 implicated in stealing trade secrets from global pharmaceutical companies.",
            "source": "https://www.pharmatechsecurity.com/RSSNewsfeed.xml",
            "title": "Pharmaceutical Trade Secrets Theft by APT76",
            "author": "Diana Brooks",
            "collected": "2024-05-14T05:50:30.123456",
            "hash": "o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
            "review": "",
            "link": "https://www.pharmasecuritytoday.com/apt76-2024.html",
            "osint_source_id": fake_source,
            "published": "2026-05-14T06:20:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk17",
            "content": "APT77 deploys disruptive attacks against national power grids in Asia.",
            "source": "https://www.energynetworksecurity.com/RSSNewsfeed.xml",
            "title": "Power Grid Disruptions in Asia by APT77",
            "author": "Evan Morales",
            "collected": "2024-05-15T04:40:14.086285",
            "hash": "p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1",
            "review": "",
            "link": "https://www.powergridsecurityfocus.com/apt77-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-15T05:05:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk18",
            "content": "APT78 targets aerospace industries with espionage aimed at stealing futuristic propulsion tech.",
            "source": "https://www.aerospaceupdates.com/RSSNewsfeed.xml",
            "title": "Espionage in Aerospace Industries by APT78",
            "author": "Fiona Garcia",
            "collected": "2024-05-16T03:30:30.123456",
            "hash": "q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2",
            "review": "",
            "link": "https://www.aerospacesecuritytoday.com/apt78-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-16T04:15:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk19",
            "content": "APT79 conducts large-scale denial of service attacks on major sports events websites during the Olympics.",
            "source": "https://www.sportssecurityupdates.com/RSSNewsfeed.xml",
            "title": "Olympic Website DDoS Attacks by APT79",
            "author": "Gregory Phillips",
            "collected": "2024-05-17T02:20:14.086285",
            "hash": "r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3",
            "review": "",
            "link": "https://www.sportseventsecurity.com/apt79-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-17T03:00:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk20",
            "content": "APT80 hacks into satellite communication systems, causing widespread disruptions in global telecommunications.",
            "source": "https://www.satellitecommsecurity.com/RSSNewsfeed.xml",
            "title": "Global Telecommunications Disrupted by APT80",
            "author": "Holly Jensen",
            "collected": "2024-05-18T01:10:30.123456",
            "hash": "s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4",
            "review": "",
            "link": "https://www.telecomsecurityupdate.com/apt80-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-18T01:45:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk13",
            "content": "APT73 exploits vulnerabilities in global shipping container tracking systems.",
            "source": "https://www.maritimesecurityupdates.com/RSSNewsfeed.xml",
            "title": "APT73 Exploits Global Shipping Container Systems",
            "author": "Aaron Carter",
            "collected": "2024-03-11T08:20:14.086285",
            "hash": "l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7",
            "review": "",
            "link": "https://www.shippingsecurityfocus.com/apt73-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-03-11T09:00:00+01:00",
        },
        {
            "id": "5o7o0071-edd3-dkl8-jkn6-nj99lkl0ooop",
            "content": "APT61 exploits vulnerabilities in IoT devices to create a large-scale botnet.",
            "source": "https://www.iotsecurityupdates.com/RSSNewsfeed.xml",
            "title": "IoT Botnet Expansion by APT61",
            "author": "Isaac Taylor",
            "collected": "2024-05-10T20:41:14.086285",
            "hash": "y4v7w2m4n10476jkf1i9j7b8c9d196l6le4hg995i8j776b1kgk5m3n3o1p028lg",
            "review": "",
            "link": "https://www.iotsecurityfocus.com/apt61-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-10T21:45:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk10",
            "content": "APT70's new cyber surveillance tools detected in international airports, raising privacy concerns.",
            "source": "https://www.airportsecuritynews.com/RSSNewsfeed.xml",
            "title": "Airport Surveillance Concerns by APT70",
            "author": "Helen York",
            "collected": "2024-05-09T01:31:30.123456",
            "hash": "i3k4l2m5n1o021pgr1h2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4",
            "review": "",
            "link": "https://www.airportsecurityfocus.com/apt70-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-09T02:30:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk11",
            "content": "APT71 exploits industrial IoT devices to launch large-scale network disruptions.",
            "source": "https://www.industrialiotsecurity.com/RSSNewsfeed.xml",
            "title": "Industrial IoT Disruptions by APT71",
            "author": "Isaac Taylor",
            "collected": "2024-01-10T00:41:14.086285",
            "hash": "j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5",
            "review": "",
            "link": "https://www.industrialiotwatch.com/apt71-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-01-10T01:45:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lk12",
            "content": "APT72 orchestrates major data breach of a renowned international museum's digital archives.",
            "source": "https://www.culturalheritagesecurity.com/RSSNewsfeed.xml",
            "title": "Major Data Breach at International Museum by APT72",
            "author": "Tina Roberts",
            "collected": "2024-02-10T09:30:00.123456",
            "hash": "k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            "review": "",
            "link": "https://www.museumsecurityupdate.com/apt72-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-02-10T10:15:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl7",
            "content": "APT67 linked to ongoing espionage operations against global mining industries.",
            "source": "https://www.miningsecurityupdates.com/RSSNewsfeed.xml",
            "title": "Global Mining Espionage by APT67",
            "author": "Jessica Watson",
            "collected": "2024-05-06T04:01:14.086285",
            "hash": "f0h5i6g0a7d87152feb7e5fe38578672ha0dc562e4c34278fdcge1i7j8l685hc",
            "review": "",
            "link": "https://www.miningsecurityupdate.com/apt67-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-06T04:46:00+01:00",
        },
        {
            "id": "9i1i4415-8ba7-7ec2-deh0-hd33edf4hfgh",
            "content": "APT55 launches a series of attacks on software development firms to inject malicious code into widely used applications.",
            "source": "https://www.softwaredesignsecurity.com/RSSNewsfeed.xml",
            "title": "Malicious Code Injection by APT55",
            "author": "Cynthia Reed",
            "collected": "2024-05-04T14:40:14.086285",
            "hash": "s8p1q6e99403686a1072d0fb2024b1b843a6736ba8ad2562780g73c8725e3f5b",
            "review": "",
            "link": "https://www.softwaresecurityfocus.com/apt55-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-04T15:25:00+01:00",
        },
        {
            "id": "0j2j5526-9c98-8fd3-efi1-ie44feg5igih",
            "content": "APT56 implicated in a cross-border hacking operation affecting several government websites.",
            "source": "https://www.govsecurityupdates.com/RSSNewsfeed.xml",
            "title": "Cross-Border Hacking by APT56",
            "author": "Derek Foster",
            "collected": "2024-05-05T15:50:30.123456",
            "hash": "t9q2r7f9g97051dea6d4ed26467563g995c439549b3159fecgf0ah6j6k5623gb",
            "review": "",
            "link": "https://www.governmentcyberwatch.com/apt56-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-05T16:35:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl1",
            "content": "APT65's malware campaign leaks sensitive information from several legal firms.",
            "source": "https://www.legalsecurityupdates.com/RSSNewsfeed.xml",
            "title": "Sensitive Data Leak by APT65",
            "author": "David Reed",
            "collected": "2024-05-04T06:20:14.086285",
            "hash": "d8f3945b722e4e44b9f0a8cf99c4457f1d9f86bf6ac2627f7f0013a451a9c5b",
            "review": "",
            "link": "https://www.legalsecurityfocus.com/apt65-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-04T07:05:00+01:00",
        },
        {
            "id": "4n6n9960-dhc2-cjk7-ijm5-mi88kjk9mnno",
            "content": "APT60 conducts cyber attacks on healthcare systems to harvest patient data for sale on the dark web.",
            "source": "https://www.healthcaresafetynews.com/RSSNewsfeed.xml",
            "title": "Patient Data Harvesting by APT60",
            "author": "Helen York",
            "collected": "2024-05-09T19:31:30.123456",
            "hash": "x3u6v1k3l09365ije0h8ih6a79b085k5kd3gf884h7f665a0jgj4l2m2n0o917kf",
            "review": "",
            "link": "https://www.healthcarecyberwatch.com/apt60-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-09T20:30:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lklm",
            "content": "APT59's new ransomware targets global shipping and logistics, demanding high ransoms.",
            "source": "https://www.logisticssecurityupdates.com/RSSNewsfeed.xml",
            "title": "Ransomware Attack on Logistics by APT59",
            "author": "Gary Newman",
            "collected": "2024-05-08T18:21:14.086285",
            "hash": "w2t5u0j2k98254hgd9g7hg5968a974j4jc2fe773g6e5549ahfi3k1l1m9n896je",
            "review": "",
            "link": "https://www.logisticssecuritytoday.com/apt59-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-08T19:15:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl8",
            "content": "APT68's advanced DDoS attacks cripple online services for multiple technology firms.",
            "source": "https://www.techsecuritynews.com/RSSNewsfeed.xml",
            "title": "Tech Firms DDoSed by APT68",
            "author": "Michael Mitchell",
            "collected": "2024-05-07T03:11:30.123456",
            "hash": "g1i7j8k2l09365ije0h8ih7b9c9d197l6le5hg996i8j787c1kgk6m4n4o2p039m",
            "review": "",
            "link": "https://www.techsecuritywatch.com/apt68-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-07T04:00:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl9",
            "content": "APT69 initiates cyber warfare tactics in conflict zones, targeting communications infrastructure.",
            "source": "https://www.warfaretechupdates.com/RSSNewsfeed.xml",
            "title": "Cyber Warfare in Conflict Zones by APT69",
            "author": "Gary Newman",
            "collected": "2024-05-08T02:21:14.086285",
            "hash": "h2j9k3l1m9n096je0i9j8a8b7c7d198m7md4gf884h8f675b2jgj5l3m4n5o1p0q",
            "review": "",
            "link": "https://www.warfaresecuritytoday.com/apt69-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-08T03:15:00+01:00",
        },
        {
            "id": "2l4l7748-bfa0-ahf5-ghk3-kg66igh7kjkl",
            "content": "APT58 uses deep learning algorithms to enhance phishing attack success rates, affecting thousands of users.",
            "source": "https://www.cyberphishingnews.com/RSSNewsfeed.xml",
            "title": "Advanced Phishing Techniques by APT58",
            "author": "Frank Mitchell",
            "collected": "2024-05-07T17:11:30.123456",
            "hash": "v1s4t9h1i98153gfc8f6gf48579873i3ib1ed662f5d44389geeh2j9k0l7857id",
            "review": "",
            "link": "https://www.phishingwatch.com/apt58-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-07T18:00:00+01:00",
        },
        {
            "id": "1k3k6637-ade9-9ge4-fgj2-jf55gfh6jijk",
            "content": "APT57 specializes in the theft of intellectual property from tech startups, threatening innovation.",
            "source": "https://www.startupsecuritynews.com/RSSNewsfeed.xml",
            "title": "Intellectual Property Theft by APT57",
            "author": "Emily Watson",
            "collected": "2024-05-06T16:01:14.086285",
            "hash": "u0r3s8g0a7d87152feb7e5fe37478672ha0dc551e4c33278fdcge1i7j8l674hc",
            "review": "",
            "link": "https://www.startupsecurityupdate.com/apt57-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-06T17:46:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl6",
            "content": "APT66 develops a powerful strain of ransomware affecting municipal government systems.",
            "source": "https://www.municipaltechsecurity.com/RSSNewsfeed.xml",
            "title": "Municipal Government Ransomware by APT66",
            "author": "Eric Foster",
            "collected": "2024-05-05T05:30:30.123456",
            "hash": "e9g4a5d8f87051dea6c3dc16456462f884b429d438a2948edcfe9g5f5e4321fa",
            "review": "",
            "link": "https://www.municipalsecuritytoday.com/apt66-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-05T06:15:00+01:00",
        },
        {
            "id": "1be00eef-6ade-4818-acfc-25029531a9a5",
            "content": "TEST CONTENT YYYY",
            "source": "https: //www.some.link/RSSNewsfeed.xml",
            "title": "Mobile World Congress 2023",
            "author": "",
            "collected": "2022-02-21T15:00:14.086285",
            "hash": "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adf",
            "review": "",
            "link": "https://www.some.other.link/2023.html",
            "osint_source_id": fake_source,
            "published": "2022-02-21T15:01:14.086285",
        },
        {
            "id": "0a129597-592d-45cb-9a80-3218108b29a0",
            "content": "TEST CONTENT XXXX",
            "source": "https: //www.content.xxxx.link/RSSNewsfeed.xml",
            "title": "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen",
            "author": "",
            "collected": "2023-01-20T15:00:14.086285",
            "hash": "e270c3a7d87051dea6c3dc14234451f884b427c32791862dacdd7a3e3d318da6",
            "review": "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten.",
            "link": "https: //www.some.other.link/BSI-Praesidentin_230207.html",
            "osint_source_id": fake_source,
            "published": "2023-01-20T19:15:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl4",
            "content": "APT62's operation exposes vulnerability in public transportation networks, leading to data breaches.",
            "source": "https://www.transportsecuritynews.com/RSSNewsfeed.xml",
            "title": "Public Transport Vulnerability Exposed by APT62",
            "author": "Claire Harrison",
            "collected": "2024-04-01T09:30:30.123456",
            "hash": "a5c1945b722e4e44b9f0a8cf99c4157f1d9f86bf6ac2026e7f0013a451a9beff",
            "review": "",
            "link": "https://www.transportsecuritytoday.com/apt62-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-04-01T10:00:00+01:00",
        },
        {
            "id": "22a13c88-8a0f-476c-b847-9e21b26311d4",
            "content": "APT28 targets European government agencies with new malware.",
            "source": "https://www.cybersecuritynews.com/RSSNewsfeed.xml",
            "title": "New Malware Campaign by APT28 Disrupted",
            "author": "Jane Doe",
            "collected": "2024-04-15T10:20:30.123456",
            "hash": "c3a1945b722e4e44b9f0a8cf99c3157f1d9f86bf6ac1226e7f0013a451a9bcdf",
            "review": "",
            "link": "https://www.techsecurityupdate.com/2024-APT28.html",
            "osint_source_id": fake_source,
            "published": "2024-04-15T11:00:00+01:00",
        },
        {
            "id": "73fa83d7-04e0-49b7-a8a7-3f29d23fc7ea",
            "content": "APT29 uses phishing to infiltrate aerospace industry databases.",
            "source": "https://www.itnews.com/RSSNewsfeed.xml",
            "title": "APT29 Phishing Attack on Aerospace Industry",
            "author": "John Smith",
            "collected": "2024-02-10T08:30:14.086285",
            "hash": "18e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1b2a",
            "review": "",
            "link": "https://www.aerospacesecurity.org/latest.html",
            "osint_source_id": fake_source,
            "published": "2024-02-10T09:00:00+01:00",
        },
        {
            "id": "3e19a0d3-c09b-4d58-af2b-6f5211962147",
            "content": "Cybersecurity firm exposes APT31's infrastructure used in recent attacks.",
            "source": "https://www.securityfocus.com/RSSNewsfeed.xml",
            "title": "Unveiling APT31's Cyber Attack Infrastructure",
            "author": "Alice Johnson",
            "collected": "2024-01-25T16:45:00.086285",
            "hash": "42d6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1c2d",
            "review": "Detailed analysis reveals the scope and technique of APT31's operations.",
            "link": "https://www.cyberdefensenews.com/apt31-exposed.html",
            "osint_source_id": fake_source,
            "published": "2024-01-25T17:30:00+01:00",
        },
        {
            "id": "5c1a82d7-3a0e-42d9-bc77-e2a1b26322e3",
            "content": "APT34 orchestrates a series of ransomware attacks against the healthcare sector.",
            "source": "https://www.medicaltechnews.com/RSSNewsfeed.xml",
            "title": "Healthcare Ransomware Surge Linked to APT34",
            "author": "Robert Lee",
            "collected": "2024-03-14T14:00:30.123456",
            "hash": "f4b1945b722e4e44b9f0a8cf99c3157f1d9f86bf6ac1226e7f0013a451a9bdcd",
            "review": "",
            "link": "https://www.healthsecuritytoday.com/ransomware-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-03-14T15:00:00+01:00",
        },
        {
            "id": "01ad82e2-4b0f-46db-b247-3e91b26311f5",
            "content": "APT35 exploits vulnerabilities in social media platforms to spread misinformation.",
            "source": "https://www.digitalnews.com/RSSNewsfeed.xml",
            "title": "APT35 Caught Spreading Misinformation Online",
            "author": "Emily Chang",
            "collected": "2024-05-20T13:20:30.123456",
            "hash": "d3a1945b722e4e44b9f0a8cf99c3157f1d9f86bf6ac1226e7f0013a451a9bfed",
            "review": "",
            "link": "https://www.socialmediasafety.com/misinfo-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-20T14:00:00+01:00",
        },
        {
            "id": "c2134c68-2a0d-45cb-a8e7-5e29c23dc7fa",
            "content": "APT37 targets research institutions with state-sponsored espionage activities.",
            "source": "https://www.researchsecurity.org/RSSNewsfeed.xml",
            "title": "State Espionage by APT37 in Research Institutions",
            "author": "Michael Brown",
            "collected": "2024-02-28T09:30:14.086285",
            "hash": "27e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1b3b",
            "review": "",
            "link": "https://www.institutesecurityupdate.com/apt37-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-02-28T10:00:00+01:00",
        },
        {
            "id": "9b1a73d7-1c0f-49b7-a8b7-6f29d23fc7eb",
            "content": "Analysis of APT38's financial cyber heists and their impact on global markets.",
            "source": "https://www.financialcyberwatch.com/RSSNewsfeed.xml",
            "title": "Global Impact of APT38's Cyber Heists",
            "author": "Linda Wright",
            "collected": "2024-03-22T12:45:00.086285",
            "hash": "52d6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1c3e",
            "review": "APT38's recent activities could affect international financial stability.",
            "link": "https://www.economicsecurity.org/apt38-heists.html",
            "osint_source_id": fake_source,
            "published": "2024-03-22T13:30:00+01:00",
        },
        {
            "id": "6e1b91c3-3b0e-42d9-acc7-e3a1b26322f4",
            "content": "APT39 exploits telecommunications networks across Asia; multiple countries affected.",
            "source": "https://www.telecomssecuritynews.com/RSSNewsfeed.xml",
            "title": "APT39's Network Exploitations Across Asia",
            "author": "Oliver King",
            "collected": "2024-04-04T11:30:30.123456",
            "hash": "g5c1945b722e4e44b9f0a8cf99c3157f1d9f86bf6ac1226e7f0013a451a9beed",
            "review": "",
            "link": "https://www.telecomsecuritytoday.com/apt39-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-04-04T12:00:00+01:00",
        },
        {
            "id": "f2213c48-6b0f-476c-b347-7e11b26312d5",
            "content": "APT40 involved in disruptive cyber-attacks against maritime shipping operations.",
            "source": "https://www.maritimesecurity.org/RSSNewsfeed.xml",
            "title": "Maritime Disruptions by APT40",
            "author": "Samantha Carter",
            "collected": "2024-05-01T14:20:30.123456",
            "hash": "h6d1945b722e4e44b9f0a8cf99c3157f1d9f86bf6ac1226e7f0013a451a9bfff",
            "review": "",
            "link": "https://www.maritimeupdate.com/apt40-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-01T15:00:00+01:00",
        },
        {
            "id": "0c12d597-4b2d-45cb-a980-3e18108b29b1",
            "content": "APT41's deepfake technology poses new threats to digital identity security.",
            "source": "https://www.identityprotectionnews.com/RSSNewsfeed.xml",
            "title": "Deepfake Dangers: APT41's New Strategy",
            "author": "Thomas Green",
            "collected": "2024-01-11T17:00:14.086285",
            "hash": "37f6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1b4c",
            "review": "",
            "link": "https://www.identitysecurity.org/deepfake-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-01-11T18:15:00+01:00",
        },
        {
            "id": "2b343fd0-a1e7-4638-bd51-99e02b29383c",
            "content": "APT42 targets major educational institutions with sophisticated phishing attacks.",
            "source": "https://www.educationsecurityupdates.com/RSSNewsfeed.xml",
            "title": "APT42's Phishing Attacks on Educational Institutions",
            "author": "Laura Peterson",
            "collected": "2024-05-10T13:00:30.123456",
            "hash": "f5b2645b722e4e44b9f0a8cf99c3257f1d9f86bf6ac1326e7f0013a451a9beff",
            "review": "",
            "link": "https://www.educationcyberwatch.com/apt42-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-10T14:00:00+01:00",
        },
        {
            "id": "7e60c7d4-95d3-4db9-a1f3-d0d23c1f0b9e",
            "content": "APT43 involved in illegal cryptocurrency mining within corporate networks.",
            "source": "https://www.cryptonewssecurity.com/RSSNewsfeed.xml",
            "title": "Corporate Network Breaches by APT43 for Crypto Mining",
            "author": "Daniel Marks",
            "collected": "2024-06-12T15:10:45.123456",
            "hash": "e4c1945b722e4e44b9f0a8cf99c4157f1d9f86bf6ac1426e7f0013a451a9beee",
            "review": "",
            "link": "https://www.cryptosecuritytoday.com/apt43-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-12T16:00:00+01:00",
        },
        {
            "id": "39f423d0-7e15-4bda-93c2-90f5b1e19b3d",
            "content": "APT44 launches denial-of-service attacks disrupting online retail services.",
            "source": "https://www.retailsecurityupdates.com/RSSNewsfeed.xml",
            "title": "Online Retail Disruptions by APT44",
            "author": "Sophie Turner",
            "collected": "2024-05-20T11:20:30.123456",
            "hash": "h7d2945b722e4e44b9f0a8cf99c4157f1d9f86bf6ac1526e7f0013a451a9befd",
            "review": "",
            "link": "https://www.retailcyberwatch.com/apt44-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-20T12:00:00+01:00",
        },
        {
            "id": "8d33a3c0-ae67-4f98-ac61-90e3b5e1988c",
            "content": "APT45 targets national power grids in a suspected sabotage campaign.",
            "source": "https://www.energysecuritynews.com/RSSNewsfeed.xml",
            "title": "National Power Grid Sabotage by APT45",
            "author": "Richard James",
            "collected": "2024-05-15T12:45:00.086285",
            "hash": "i8e3e99403686a1072d0fb2013901b843a6725ba8ac1626270f62b7614ec1b5d",
            "review": "",
            "link": "https://www.energysecurityupdate.com/apt45-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-15T13:30:00+01:00",
        },
        {
            "id": "fe12d397-5d2d-4cbc-9a80-3f18105b2970",
            "content": "APT46 implicated in data breaches affecting multinational banking institutions.",
            "source": "https://www.financialsecurity.org/RSSNewsfeed.xml",
            "title": "Data Breaches in Banking by APT46",
            "author": "Megan Clarke",
            "collected": "2024-05-30T09:00:14.086285",
            "hash": "j9f6f99403686a1072d0fb2013901b843a6725ba8ac1726270f62b7614ec1c6f",
            "review": "",
            "link": "https://www.bankingsecurityfocus.com/apt46-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-30T10:15:00+01:00",
        },
        {
            "id": "ad23b3d0-9f10-4bd8-bf62-81f5b1c19b4e",
            "content": "APT47 uses AI-driven bots to manipulate stock market transactions.",
            "source": "https://www.marketmanipulationnews.com/RSSNewsfeed.xml",
            "title": "Stock Market Manipulation by APT47",
            "author": "Nathan Ross",
            "collected": "2024-05-11T14:20:30.123456",
            "hash": "k0g3h945b722e4e44b9f0a8cf99d3157f1d9f86bf6ac1826e7f0013a451a9cdd",
            "review": "",
            "link": "https://www.financialintegritywatch.com/apt47-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-11T15:00:00+01:00",
        },
        {
            "id": "be34c3e0-cf17-4f89-bd61-92e4b5f1989d",
            "content": "APT48 launches attacks on satellite communications, causing widespread disruption.",
            "source": "https://www.satellitecomsecurity.com/RSSNewsfeed.xml",
            "title": "Satellite Communications Disrupted by APT48",
            "author": "Olivia Green",
            "collected": "2024-05-05T10:45:00.086285",
            "hash": "l1h4i99403686a1072d0fb2013901b843a6725ba8ac1926270f62b7614ec1d7g",
            "review": "",
            "link": "https://www.spacecomsecupdate.com/apt48-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-05T11:30:00+01:00",
        },
        {
            "id": "cf45d4f0-d018-4cda-c063-83g6c2e1ab5f",
            "content": "APT49's new malware variant bypasses conventional antivirus software.",
            "source": "https://www.antivirusfails.com/RSSNewsfeed.xml",
            "title": "New Malware by APT49 Evades Detection",
            "author": "Peter Franklin",
            "collected": "2024-05-25T16:00:30.123456",
            "hash": "m2i5j0a7d87051dea6c3dc14234451f884b427c32791862dacdd7a3e3d318da7",
            "review": "",
            "link": "https://www.antiviruswatch.com/apt49-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-25T17:00:00+01:00",
        },
        {
            "id": "dg56e5g1-e119-5edb-d064-94h7d3f2bc6g",
            "content": "APT50 accused of infiltrating government defense networks to steal classified information.",
            "source": "https://www.defensenetworknews.com/RSSNewsfeed.xml",
            "title": "Classified Data Theft by APT50",
            "author": "Rachel Evans",
            "collected": "2024-01-15T11:15:30.123456",
            "hash": "n3j6k1b8e8d97051dea6c3dc14234451f884b427c32791862dacdd7a3e3d319d8",
            "review": "",
            "link": "https://www.nationalsecurityupdates.com/apt50-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-01-15T12:00:00+01:00",
        },
        {
            "id": "eh67f6h2-f220-6fec-e065-95i8e4g3cd7h",
            "content": "APT51's cyber-espionage campaign targets global pharmaceutical companies.",
            "source": "https://www.pharmasecuritynews.com/RSSNewsfeed.xml",
            "title": "Cyber-Espionage in Pharma by APT51",
            "author": "Michelle Liu",
            "collected": "2024-02-28T09:30:14.086285",
            "hash": "o4k7l2c9f9f08151fea6d4ed25345561g995c438438a2937edbfe8f4e4d320e9",
            "review": "",
            "link": "https://www.pharmasecurityfocus.com/apt51-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-02-28T10:15:00+01:00",
        },
        {
            "id": "6f7f1182-5874-4b99-ade7-ea007ba1ecef",
            "content": "APT52 deploys new rootkit aimed at cloud infrastructures to steal corporate data.",
            "source": "https://www.cloudtechnews.com/RSSNewsfeed.xml",
            "title": "New Cloud Rootkit by APT52 Exposed",
            "author": "Steve Harrison",
            "collected": "2024-03-01T12:00:30.123456",
            "hash": "p5m8n3b722e4e44b9f0a8cf99d4257f1d9f86bf6ac2026e7f0013a451a9cfdd",
            "review": "",
            "link": "https://www.cloudsecuritytoday.com/apt52-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-03-01T12:45:00+01:00",
        },
        {
            "id": "7g8g2293-6985-5ca0-bcf8-fb118cb2fdef",
            "content": "APT53 targets diplomatic communications in Europe with sophisticated cyber espionage tactics.",
            "source": "https://www.diplomacysecurityupdates.com/RSSNewsfeed.xml",
            "title": "Diplomatic Espionage by APT53 in Europe",
            "author": "Angela Meyer",
            "collected": "2024-04-02T10:20:14.086285",
            "hash": "q6n9o4c99403686a1072d0fb2014a1b843a6725ba8ac2326270f62b7614ed2de",
            "review": "",
            "link": "https://www.diplomaticsecurityfocus.com/apt53-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-04-02T11:00:00+01:00",
        },
        {
            "id": "8h9h3304-7a96-6db1-cdg9-gc229dc3gefg",
            "content": "APT54 develops malware that disrupts industrial control systems, risking severe impacts on national infrastructure.",
            "source": "https://www.industrialsecuritynews.com/RSSNewsfeed.xml",
            "title": "Industrial Malware Threat by APT54",
            "author": "Brian Scott",
            "collected": "2024-05-03T13:30:30.123456",
            "hash": "r7o0p5d8f87051dea6c3dc15356462f884b428d438a2948edcfe9g5f5e4321fa",
            "review": "",
            "link": "https://www.industrialsecuritytoday.com/apt54-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-03T14:15:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl3",
            "content": "APT63 employs AI to create advanced spear-phishing campaigns targeting political figures.",
            "source": "https://www.politicalsecurityupdates.com/RSSNewsfeed.xml",
            "title": "APT63's AI Spear-Phishing Targeting Political Figures",
            "author": "Martin Meyer",
            "collected": "2024-05-02T08:40:14.086285",
            "hash": "b6d1945b722e4e44b9f0a8cf99c4257f1d9f86bf6ac2326270f62b7614ed2de",
            "review": "",
            "link": "https://www.politicalsecurityfocus.com/apt63-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-02T09:15:00+01:00",
        },
        {
            "id": "3m5m8859-cgb1-bij6-hil4-lh77jij8lkl2",
            "content": "APT64 suspected in the cyber attack that disrupted global stock exchanges last week.",
            "source": "https://www.financialmarketsecurity.com/RSSNewsfeed.xml",
            "title": "Global Stock Exchange Disruption by APT64",
            "author": "Susan Scott",
            "collected": "2024-05-03T07:50:30.123456",
            "hash": "c7e2945b722e4e44b9f0a8cf99c4357f1d9f86bf6ac2526e7f0013a451a9befd",
            "review": "",
            "link": "https://www.financialsecuritytoday.com/apt64-2024.html",
            "osint_source_id": fake_source,
            "published": "2024-05-03T08:30:00+01:00",
        },
        {
            "id": "5f730743-5eec-42b1-95b6-0ececbe1d2bb",
            "content": "Security researchers have identified a new ransomware variant that specifically targets cloud storage services.",
            "source": "https://www.cybersecurityinsights.com/RSSNewsfeed.xml",
            "title": "New Ransomware Targets Cloud Environments",
            "author": "James Corwin",
            "collected": "2000-12-07T00:59:12",
            "hash": "abce201fc86f06adad8a6a83c0492d9f616246d19c8659b8f2c55466dd98db84",
            "review": "",
            "link": "https://www.cybersecurityinsights.com/new-cloud-ransomware-2000.html",
            "osint_source_id": fake_source,
            "published": "2000-07-09T17:23:53",
        },
        {
            "id": "48f1e64f-f69f-4057-809a-48f706746fac",
            "content": "A critical zero-day vulnerability has been discovered in a widely-used web server, potentially exposing millions of websites.",
            "source": "https://www.infosecurityalerts.com/RSSNewsfeed.xml",
            "title": "Zero-Day Exploit Found in Popular Web Server",
            "author": "Alice Johnson",
            "collected": "2000-05-28T19:41:16",
            "hash": "42cf38bfa93f10105907cc5e38122d751711867560216bda3c085ac94598524c",
            "review": "",
            "link": "https://www.infosecurityalerts.com/web-server-zero-day-2000.html",
            "osint_source_id": fake_source,
            "published": "2000-10-30T23:40:15",
        },
        {
            "id": "78f04d84-2c69-4c79-9e9c-39bf0dabd652",
            "content": "Reports indicate that a nation-state-backed hacking group attempted to compromise a major power grid system.",
            "source": "https://www.criticalinfrastructuredefense.com/RSSNewsfeed.xml",
            "title": "Nation-State Attack Targets Power Grid",
            "author": "Robert Fields",
            "collected": "2000-10-28T23:49:51",
            "hash": "ee860310326d121df31939d4983109e4e3e09eaf043563f2f63162a5611d916a",
            "review": "",
            "link": "https://www.criticalinfrastructuredefense.com/power-grid-attack-2000.html",
            "osint_source_id": fake_source,
            "published": "2000-04-23T15:12:08",
        },
        {
            "id": "11e1f348-d53b-4542-ae1d-2674be32184c",
            "content": "Hackers have leaked sensitive financial records from multiple banking institutions in a major data breach.",
            "source": "https://www.financialcybernews.com/RSSNewsfeed.xml",
            "title": "Massive Data Breach Affects Financial Institutions",
            "author": "Emma Thompson",
            "collected": "2000-12-07T09:38:04",
            "hash": "aa1e774c2472536492d1de70dad65e7d052df1e524051c5075dd6fb0ece09b7b",
            "review": "",
            "link": "https://www.financialcybernews.com/banking-data-breach-2000.html",
            "osint_source_id": fake_source,
            "published": "2000-04-27T01:51:09",
        },
        {
            "id": "e300742f-124f-4e2f-ab3f-bb80b34b1d01",
            "content": "Researchers have discovered malware embedded in popular open-source libraries used by thousands of applications.",
            "source": "https://www.softwaresecuritywatch.com/RSSNewsfeed.xml",
            "title": "Malware Hidden in Open-Source Libraries",
            "author": "Michael Carter",
            "collected": "2000-07-30T09:59:45",
            "hash": "9e238034dfedd2fa790822818a13014fbd62c9b4b16c3e8ff7b54da29b68e7c4",
            "review": "",
            "link": "https://www.softwaresecuritywatch.com/open-source-malware-2000.html",
            "osint_source_id": fake_source,
            "published": "2000-03-14T08:58:59",
        },
    ]


@pytest.fixture(scope="session")
def create_html_render(app):
    # fixture returns a callable, so that we can choose the time to execute it
    def get_product_to_render():
        with app.app_context():
            from core.model.product import Product
            from core.managers.db_manager import db

            # get id of first product in product table
            if product := Product.get_first(db.select(Product)):
                product_id = product.id
            else:
                product_id = "test"

            # test html for product rendering
            test_html = "Thanks to Cybersecurity experts, the world of IT is now safe."

            Product.update_render_for_id(product_id, test_html)

    return get_product_to_render
