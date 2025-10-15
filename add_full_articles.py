# add_full_articles.py
import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from news.models import Category, News

# ensure categories exist
categories = ['World', 'Politics', 'Tech', 'Sports', 'Entertainment']
for c in categories:
    Category.objects.get_or_create(name=c)
cats = {c.name: c for c in Category.objects.all()}

# Map titles to new full content and category (if needed)
updates = {
    "Breakthrough Cancer Therapy Shows Promising Results": {
        "content": """Researchers announced today that a novel targeted therapy has produced significant tumor shrinkage in early-stage clinical trials, offering what many scientists are calling a genuine reason for cautious optimism. The experimental treatment — which combines an engineered antibody with a precision-delivery nanoparticle — is designed to home in on a specific receptor found predominantly on tumor cells while sparing healthy tissue. Trial participants with aggressive solid tumors experienced measurable reductions in tumor volume, and several patients reported improved quality of life indicators within weeks of starting therapy.

Molecular analysis shows that the drug achieves its effect through a two-step mechanism: first, the antibody portion binds tightly and selectively to the tumor cell receptor; second, the nanoparticle releases a cytotoxic agent directly inside the matched cells. This targeted delivery reduces systemic exposure and therefore limits side effects commonly associated with conventional chemotherapy. According to the lead investigator, adverse events so far have been mostly mild to moderate and manageable with standard supportive care.

Experts caution that while early-phase results are encouraging, further testing is needed. These trials are designed primarily to evaluate safety and to identify an appropriate dose. Larger Phase III studies — which would compare this treatment directly with existing standards of care — are still required before regulatory approval can be considered. Still, patient advocates and academic oncologists highlight that new modalities that increase response rates while lowering toxicity would be a major advance.

In addition to clinical endpoints, researchers are monitoring biomarkers that may predict which patients will benefit most. Early signals suggest that tumors with higher expression of the target receptor show better responses. If validated, this would enable physicians to personalize treatment by selecting patients most likely to benefit. Pharmaceutical partners have said they are expediting manufacturing and regulatory planning to accelerate the next-stage trials.""",
        "category": cats['World']
    },

    "Elections 2025: Key Takeaways from Last Night": {
        "content": """Voter turnout surged in multiple regions overnight as citizens cast ballots in a series of closely watched legislative and gubernatorial races. Early returns suggest several unexpected upsets that will reshape the political map heading into the next legislative session. Analysts point to a combination of local issues, shifting coalitions, and vigorous grassroots mobilization as driving forces behind the surprises.

Several districts that had been considered safe for incumbents flipped to challengers, altering the balance of power in statehouses and councils. Pundits attribute these results to voter concerns over housing affordability, public safety, and recent economic pressures. Exit polls indicate that younger voters and first-time participants were decisive in a number of tight contests.

Party leaders are now assessing the implications for national strategy. For the party that gained seats, the wins provide momentum and an opportunity to push priority legislation in the coming months; for the party that lost ground, there will be an intense period of internal review and leadership recalibration. Observers also noted a record number of women and candidates from underrepresented communities winning office, marking a notable change in candidate diversity.

As official counts continue and some close races proceed to recounts, attention will shift to coalition-building and policy negotiations. Stakeholders on both sides emphasize the need to respect the democratic process and to prepare for governance transitions. International observers and trade partners are watching closely; stable handoffs and adherence to procedural norms remain key for investor confidence and diplomatic relations.""",
        "category": cats['Politics']
    },

    "New Phone Launch: What's Different This Year": {
        "content": """The latest flagship phone unveiled today promises substantial improvements across the board — from battery life and display tech to camera capabilities and software optimization. The manufacturer is marketing the device as a step-change in durability and multimedia performance, highlighting a flexible OLED panel, a larger battery matched with smarter power management, and a revamped camera stack designed for both still and computational video capture.

A major hardware highlight is the hybrid cooling and power system that allows sustained performance for gaming and heavy workloads while keeping thermal throttling under control. Benchmarks released by independent reviewers show comparative gains in sustained performance and battery longevity versus previous models. On the software side, the operating system includes new energy-aware scheduling and tighter integration between apps and system services to reduce background power draw.

The camera system pushes further into computational photography, offering advanced HDR video recording, a dedicated night video mode, and a multi-frame stacking algorithm that improves low-light detail without introducing noise. For creators, there are new pro controls and a suite of editing tools built into the gallery app. Connectivity improvements include faster mmWave and sub-6GHz compatibility where available, plus expanded satellite-assisted messaging in emergencies.

Pricing and availability will vary by region, and the company is introducing a trade-in program and flexible financing to ease the cost for upgraders. Critics point to the high starting price as an adoption barrier, but many reviewers conclude that for users who rely heavily on cameras and gaming, the upgrades offer real value. The device launches in stores and carrier channels next month.""",
        "category": cats['Tech']
    },

    "City Wins Comeback Thriller in Final Seconds": {
        "content": """In a game that will be talked about for weeks, City clinched a dramatic comeback with a buzzer-beater that left the home crowd stunned and elated. Trailing by double digits with under ten minutes left, the team staged a coordinated effort on both ends — a tightened defense, high-energy substitutions, and a series of fast-breaks — to chip away at the lead. The final sequence saw a series of contested shots before the go-ahead three-pointer from the team’s veteran guard with just 0.6 seconds remaining.

Coaches and players praised the team’s composure under pressure. The defensive adjustments made during the fourth quarter forced turnovers and limited the opposing team’s looks from the perimeter. Statistically, the comeback was built on improved rebounding and smart ball movement; the winning team recorded lower turnover numbers late in the game and capitalized on second-chance opportunities.

The victory has immediate playoff implications and raises questions about momentum heading into the league’s final stretch. Analysts say the team’s resilience will be a psychological boost, but they also highlight areas for improvement — notably interior defense consistency and free-throw shooting under duress. Fans celebrated long into the night, and social channels lit up with highlights and reaction clips.

Postgame interviews focused on leadership and preparation. The coach credited veteran leadership for steadying the younger players, while the veteran guard who hit the final shot downplayed individual heroics and emphasized collective effort. The opposing team, meanwhile, expressed disappointment but vowed to regroup quickly for their next matchup.""",
        "category": cats['Sports']
    },

    "Film Festival Highlights: The Year's Best Indies": {
        "content": """The city’s film festival wrapped up with a slate of independent features and shorts that showcased daring storytelling, inventive cinematography, and bold directorial debuts. Several films that premiered at the festival are already generating awards-season buzz for their raw performances and tightly focused narratives. Critics praised a cross-section of films that explore identity, economic dislocation, and the human consequences of technological change.

Standout entries included a small ensemble drama that used a single location to unpack family dynamics with razor-sharp dialogue, a visually bold sci-fi meditation on memory and loss, and a documentary that followed grassroots environmental organizers over a decade. The festival’s programming director said this year’s lineup reflected a renewed appetite for intimate, character-driven stories that trust audiences to engage with ambiguity and moral complexity.

Industry panels held alongside screenings emphasized the evolving landscape of independent distribution, including hybrid release strategies that combine festival exposure with targeted streaming deals. Filmmakers discussed the challenges of financing and the creative freedoms that smaller budgets can sometimes enable. Attendees noted that the festival’s marketplace facilitated connections between auteurs and boutique distributors eager for distinctive content.

Several breakout directors were singled out as talent to watch. Critics also noted the festival’s continued commitment to representing voices from underrepresented communities and to curating a program that balances entertainment with social inquiry. As deals are announced and films roll out to wider audiences, the festival’s influence is likely to extend into broader cinematic conversation for the months ahead.""",
        "category": cats['Entertainment']
    }
}

# apply updates
updated = []
for title, payload in updates.items():
    try:
        obj = News.objects.get(title=title)
    except News.DoesNotExist:
        print("News not found with title:", title)
        continue

    obj.content = payload['content']
    # keep created_at unchanged; do not modify images
    obj.save()
    updated.append((obj.id, obj.title))

print("Updated articles:", updated)
