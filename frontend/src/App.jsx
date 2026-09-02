import { useEffect, useState } from "react"
import {
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  Heart,
  LogOut,
  Search,
  Settings2,
  Sparkles,
  UserRound,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"

const platforms = ["All platforms", "Coursera", "Udemy"]
const levels = ["Any level", "Beginner", "Intermediate", "Advanced"]
const categories = [
  "Any category",
  "Business",
  "Computer Science",
  "Data Science",
  "Information Technology",
  "Language Learning",
  "Personal Development",
]
const learningStatuses = ["Exploring", "Learning actively", "Building projects", "Career switching"]

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong. Please try again.")
  }

  return data
}

function App() {
  const [user, setUser] = useState(null)
  const [view, setView] = useState("discover")
  const [interests, setInterests] = useState("")
  const [platform, setPlatform] = useState("All platforms")
  const [level, setLevel] = useState("Any level")
  const [category, setCategory] = useState("Any category")
  const [recommendations, setRecommendations] = useState([])
  const [explanation, setExplanation] = useState("")
  const [activity, setActivity] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [welcomeName, setWelcomeName] = useState("")
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState("login")
  const [authForm, setAuthForm] = useState({ username: "", email: "", password: "" })
  const [profileForm, setProfileForm] = useState(emptyProfile())

  useEffect(() => {
    apiFetch("/api/me")
      .then((data) => {
        setUser(data.user)
        if (data.user) setProfileForm(profileFromUser(data.user))
      })
      .catch(() => setUser(null))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const googleError = params.get("google_error")
    const googleLogin = params.get("google_login")
    if (googleLogin === "success") {
      apiFetch("/api/me")
        .then((data) => {
          setUser(data.user)
          setProfileForm(profileFromUser(data.user))
          setWelcomeName(data.user?.username || "there")
        })
        .catch(() => setError("Google sign-in succeeded, but we could not load your profile."))
      window.history.replaceState({}, "", window.location.pathname)
      return
    }

    if (!googleError) return

    setError(googleError)
    window.history.replaceState({}, "", window.location.pathname)
  }, [])

  function showError(text) {
    setMessage("")
    setError(text)
  }

  function showMessage(text) {
    setError("")
    setMessage(text)
  }

  async function searchCourses(event) {
    event.preventDefault()
    if (!interests.trim()) {
      showError("Tell us what you would like to learn first.")
      return
    }

    setError("")
    setMessage("")
    setLoading(true)

    try {
      const data = await apiFetch("/api/recommendations", {
        method: "POST",
        body: JSON.stringify({ interests, platform, level, category }),
      })
      setRecommendations(data.recommendations)
      setExplanation(data.explanation)
    } catch (requestError) {
      showError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  async function saveCourse(course) {
    if (!user) {
      setAuthMode("login")
      setAuthOpen(true)
      showMessage("Sign in to save courses to your learning list.")
      return
    }

    try {
      const data = await apiFetch("/api/saved-courses", {
        method: "POST",
        body: JSON.stringify({
          course_id: course.course_id,
          course_title: course.title,
          search_query: interests,
        }),
      })
      showMessage(data.message)
    } catch (requestError) {
      showError(requestError.message)
    }
  }

  async function trackCourse(course, action) {
    if (!user) {
      setAuthMode("login")
      setAuthOpen(true)
      showMessage("Sign in to track your course progress.")
      return
    }

    try {
      const data = await apiFetch(`/api/course-actions/${action}`, {
        method: "POST",
        body: JSON.stringify({
          course_id: course.course_id,
          course_title: course.title,
          search_query: interests,
        }),
      })
      showMessage(data.message)
    } catch (requestError) {
      showError(requestError.message)
    }
  }

  async function submitAuth(event) {
    event.preventDefault()
    setError("")

    const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/register"
    const body = authMode === "login"
      ? { email: authForm.email, password: authForm.password }
      : authForm

    try {
      const data = await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      })
      setUser(data.user)
      setProfileForm(profileFromUser(data.user))
      setAuthForm({ username: "", email: "", password: "" })
      setAuthOpen(false)
      showMessage(
        authMode === "login"
          ? `Welcome back, ${data.user.username}!`
          : `Welcome to Coursewise, ${data.user.username}!`
      )
    } catch (requestError) {
      showError(requestError.message)
    }
  }

  async function loadActivity() {
    try {
      const data = await apiFetch("/api/activity")
      setActivity(data)
      setView("activity")
      setError("")
    } catch (requestError) {
      showError(requestError.message)
    }
  }

  async function removeSavedCourse(interactionId) {
    try {
      const data = await apiFetch(`/api/saved-courses/${interactionId}`, {
        method: "DELETE",
      })
      showMessage(data.message)
      await loadActivity()
    } catch (requestError) {
      showError(requestError.message)
    }
  }

  async function saveProfile(event) {
    event.preventDefault()
    try {
      const data = await apiFetch("/api/profile", {
        method: "PUT",
        body: JSON.stringify(profileForm),
      })
      setUser(data.user)
      setProfileForm(profileFromUser(data.user))
      showMessage(data.message)
    } catch (requestError) {
      showError(requestError.message)
    }
  }

  async function logout() {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" })
    } catch {
      // The local session is still cleared below if the backend has already stopped.
    }
    setUser(null)
    setProfileForm(emptyProfile())
    setView("discover")
    setActivity(null)
    showMessage("You have been logged out.")
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <button className="flex items-center gap-2 text-xl font-semibold tracking-tight" onClick={() => setView("discover")}>
            <span className="grid size-9 place-items-center rounded-xl bg-slate-950 text-white"><BookOpen className="size-5" /></span>
            Coursewise
          </button>

          <nav className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => setView("discover")}>Discover</Button>
            {user ? (
              <>
                <Button variant="ghost" onClick={loadActivity}>My learning</Button>
                <Button variant="ghost" onClick={() => setView("profile")}>
                  <Settings2 className="size-4" /> Profile
                </Button>
                <span className="hidden items-center gap-2 px-2 text-sm text-slate-600 xl:flex"><UserRound className="size-4" /> {user.username}</span>
                <Button variant="outline" onClick={logout}><LogOut className="size-4" /> Log out</Button>
              </>
            ) : (
              <Button onClick={() => { setAuthMode("login"); setAuthOpen(true) }}>Sign in</Button>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-12 lg:px-8">
        {welcomeName && (
          <WelcomeBanner
            name={welcomeName}
            onDismiss={() => setWelcomeName("")}
          />
        )}
        {message && <Notice tone="success">{message}</Notice>}
        {error && <Notice tone="error">{error}</Notice>}

        {view === "discover" && (
          <Discover
            interests={interests}
            setInterests={setInterests}
            platform={platform}
            setPlatform={setPlatform}
            level={level}
            setLevel={setLevel}
            category={category}
            setCategory={setCategory}
            loading={loading}
            onSearch={searchCourses}
            recommendations={recommendations}
            explanation={explanation}
            onSave={saveCourse}
            onTrack={trackCourse}
          />
        )}
        {view === "activity" && <ActivityView activity={activity} onDiscover={() => setView("discover")} onRemoveSaved={removeSavedCourse} />}
        {view === "profile" && user && (
          <ProfileView
            user={user}
            profileForm={profileForm}
            setProfileForm={setProfileForm}
            onSave={saveProfile}
          />
        )}
      </main>

      {authOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 p-4">
          <Card className="w-full max-w-md shadow-xl">
            <CardHeader>
              <CardTitle>{authMode === "login" ? "Welcome back" : "Create your account"}</CardTitle>
              <CardDescription>Save courses, track your learning, and build a personal profile.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" variant="outline" onClick={() => window.location.assign("/api/auth/google")}>Continue with Google</Button>
              <div className="my-4 flex items-center gap-3 text-xs text-slate-500 before:h-px before:flex-1 before:bg-slate-200 after:h-px after:flex-1 after:bg-slate-200">or</div>
              <form className="grid gap-4" onSubmit={submitAuth}>
                {authMode === "register" && <Input placeholder="Username" value={authForm.username} onChange={(event) => setAuthForm({ ...authForm, username: event.target.value })} />}
                <Input placeholder="Email address" type="email" value={authForm.email} onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })} />
                <Input placeholder="Password" type="password" value={authForm.password} onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })} />
                <Button type="submit">{authMode === "login" ? "Sign in" : "Create account"}</Button>
              </form>
              <button className="mt-4 text-sm font-medium text-slate-600 underline underline-offset-4" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>{authMode === "login" ? "Need an account? Create one" : "Already have an account? Sign in"}</button>
              <button className="mt-3 block text-sm text-slate-500" onClick={() => setAuthOpen(false)}>Continue without an account</button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

function Discover(props) {
  return (
    <>
      <section className="mb-8 max-w-3xl">
        <Badge variant="secondary" className="mb-4 px-3 py-1"><Sparkles className="size-3.5" /> AI-powered course discovery</Badge>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">Learn what moves you forward.</h1>
        <p className="mt-4 text-lg leading-8 text-slate-600">Search a combined Coursera and Udemy catalog, then get a clear reason why each recommendation fits.</p>
      </section>

      <Card className="mb-10 shadow-sm">
        <CardContent className="pt-6">
          <form className="grid gap-4 lg:grid-cols-12" onSubmit={props.onSearch}>
            <label className="grid gap-2 lg:col-span-5"><span className="text-sm font-medium">What do you want to learn?</span><Input className="h-11" placeholder="Python, cloud computing, data analysis..." value={props.interests} onChange={(event) => props.setInterests(event.target.value)} /></label>
            <FilterSelect label="Platform" value={props.platform} options={platforms} onChange={props.setPlatform} />
            <FilterSelect label="Level" value={props.level} options={levels} onChange={props.setLevel} />
            <FilterSelect label="Category" value={props.category} options={categories} onChange={props.setCategory} />
            <div className="flex items-end lg:col-span-1"><Button className="h-11 w-full" disabled={props.loading} type="submit"><Search className="size-4" /> {props.loading ? "Searching" : "Search"}</Button></div>
          </form>
        </CardContent>
      </Card>

      {props.explanation && <Card className="mb-8 border-amber-200 bg-amber-50 shadow-none"><CardHeader><CardTitle className="flex items-center gap-2 text-amber-950"><Sparkles className="size-5" /> Why your top match fits</CardTitle><CardDescription className="text-amber-900">{props.explanation}</CardDescription></CardHeader></Card>}

      {props.recommendations.length > 0 && <section><div className="mb-5 flex items-center justify-between"><div><h2 className="text-2xl font-semibold tracking-tight">Recommended for you</h2><p className="mt-1 text-sm text-slate-500">Ranked by similarity, preference filters, and course quality.</p></div><Badge variant="outline">{props.recommendations.length} matches</Badge></div><div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{props.recommendations.map((course, index) => <CourseCard key={`${course.course_id}-${index}`} course={course} onSave={props.onSave} onTrack={props.onTrack} />)}</div></section>}
    </>
  )
}

function FilterSelect({ label, value, options, onChange }) {
  return <label className="grid gap-2 lg:col-span-2"><span className="text-sm font-medium">{label}</span><select className="h-11 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus:ring-3 focus:ring-ring/40" value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option}>{option}</option>)}</select></label>
}

function CourseCard({ course, onSave, onTrack }) {
  const score = Math.round(Number(course.final_score) * 100)
  return <Card className="shadow-sm transition-shadow hover:shadow-md"><CardHeader><div className="flex items-start justify-between gap-3"><Badge variant="secondary">{course.platform}</Badge><span className="text-sm font-medium text-slate-500">{score}% match</span></div><CardTitle className="mt-2 line-clamp-2 text-lg">{course.title}</CardTitle><CardDescription>{course.category} · {course.level}</CardDescription></CardHeader><CardContent className="grid gap-3"><span className="text-sm text-slate-600">★ {course.rating || "Not rated"}</span>{course.explanation_factors?.length > 0 && <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600"><span className="font-semibold text-slate-800">Why it ranked: </span>{course.explanation_factors.map((item) => item.factor).join(", ")}</div>}<div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => window.open(course.course_link, "_blank", "noopener,noreferrer")}>Open <ArrowUpRight className="size-3.5" /></Button><Button size="sm" onClick={() => onSave(course)}><Heart className="size-3.5" /> Save</Button><Button size="sm" variant="secondary" onClick={() => onTrack(course, "enrolled")}>Enrolled</Button><Button size="sm" variant="ghost" onClick={() => onTrack(course, "completed")}><CheckCircle2 className="size-3.5" /> Complete</Button></div></CardContent></Card>
}

function ActivityView({ activity, onDiscover, onRemoveSaved }) {
  if (!activity) return <p className="text-slate-600">Loading your learning activity…</p>

  return (
    <section>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Badge variant="secondary" className="mb-4 px-3 py-1">Learning profile</Badge>
          <h1 className="text-4xl font-semibold tracking-tight">Your activity</h1>
          <p className="mt-3 text-lg text-slate-600">Track the courses you saved, enrolled in, and completed.</p>
        </div>
        <Button variant="outline" onClick={onDiscover}>Discover courses</Button>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Metric label="Saved" value={activity.summary?.saved || 0} />
        <Metric label="Enrolled" value={activity.summary?.enrolled || 0} />
        <Metric label="Completed" value={activity.summary?.completed || 0} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <CourseActivityList
          title="Saved courses"
          icon={<Heart className="size-5" />}
          items={activity.saved_courses || []}
          emptyText="No saved courses yet."
          onRemove={onRemoveSaved}
        />
        <CourseActivityList
          title="Enrolled courses"
          icon={<BookOpen className="size-5" />}
          items={activity.enrolled_courses || []}
          emptyText="No enrolled courses yet."
        />
        <CourseActivityList
          title="Completed courses"
          icon={<CheckCircle2 className="size-5" />}
          items={activity.completed_courses || []}
          emptyText="No completed courses yet."
        />
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Clock3 className="size-5" /> Search history</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          {(activity.search_history || []).length ? activity.search_history.map((item) => (
            <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-4 last:border-0" key={item.id}>
              <span className="font-medium">{item.search_query}</span>
              <Badge variant="outline">{item.course_count} matches</Badge>
            </div>
          )) : <p className="text-sm text-slate-500">No searches yet.</p>}
        </CardContent>
      </Card>
    </section>
  )
}

function CourseActivityList({ title, icon, items, emptyText, onRemove }) {
  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2">{icon} {title}</CardTitle></CardHeader>
      <CardContent className="grid gap-4">
        {items.length ? items.map((item) => (
          <div className="border-b border-slate-100 pb-4 last:border-0" key={item.id}>
            <div className="flex items-start justify-between gap-3">
              <p className="font-medium leading-snug">{item.course_title}</p>
              {onRemove && <Button size="sm" variant="ghost" onClick={() => onRemove(item.id)}>Remove</Button>}
            </div>
            <p className="mt-2 text-sm text-slate-500">From search: “{item.search_query || "Coursewise"}”</p>
          </div>
        )) : <p className="text-sm text-slate-500">{emptyText}</p>}
      </CardContent>
    </Card>
  )
}

function Metric({ label, value }) {
  return <Card className="shadow-sm"><CardContent className="pt-5"><p className="text-sm text-slate-500">{label}</p><p className="mt-1 text-3xl font-semibold tracking-tight">{value}</p></CardContent></Card>
}

function ProfileView({ user, profileForm, setProfileForm, onSave }) {
  return <section className="max-w-3xl"><Badge variant="secondary" className="mb-4 px-3 py-1">Personalise your recommendations</Badge><h1 className="text-4xl font-semibold tracking-tight">Your learner profile</h1><p className="mt-3 text-lg text-slate-600">Tell Coursewise where you are now and what you want to achieve. These details will guide future recommendations.</p><Card className="mt-8 shadow-sm"><CardHeader><CardTitle>{user.username}</CardTitle><CardDescription>{user.email}</CardDescription></CardHeader><CardContent><form className="grid gap-5" onSubmit={onSave}><ProfileSelect label="Current learning status" value={profileForm.learning_status} options={learningStatuses} onChange={(value) => setProfileForm({ ...profileForm, learning_status: value })} /><ProfileSelect label="Your current level" value={profileForm.learning_level} options={levels.slice(1)} onChange={(value) => setProfileForm({ ...profileForm, learning_level: value })} /><label className="grid gap-2"><span className="text-sm font-medium">Learning goal</span><Input className="h-11" placeholder="Example: Move into a cloud engineering role" value={profileForm.learning_goal} onChange={(event) => setProfileForm({ ...profileForm, learning_goal: event.target.value })} /></label><label className="grid gap-2"><span className="text-sm font-medium">Skills you already have</span><textarea className="min-h-28 rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-3 focus:ring-ring/40" placeholder="Example: Python, Excel, SQL basics, communication" value={profileForm.skills} onChange={(event) => setProfileForm({ ...profileForm, skills: event.target.value })} /></label><Button className="w-fit" type="submit">Save profile</Button></form></CardContent></Card></section>
}

function ProfileSelect({ label, value, options, onChange }) {
  return <label className="grid gap-2"><span className="text-sm font-medium">{label}</span><select className="h-11 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:ring-3 focus:ring-ring/40" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Choose an option</option>{options.map((option) => <option key={option}>{option}</option>)}</select></label>
}

function Notice({ tone, children }) {
  const colors = tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-800"
  return <div className={`mb-6 rounded-xl border px-4 py-3 text-sm font-medium ${colors}`}>{children}</div>
}

function WelcomeBanner({ name, onDismiss }) {
  return (
    <div className="relative mb-8 overflow-hidden rounded-2xl bg-slate-950 px-6 py-7 text-white shadow-lg sm:px-8">
      <Sparkles className="absolute -right-3 -top-3 size-24 text-cyan-300/15" />
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-cyan-200">Google sign-in successful</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Welcome, {name}!</h2>
      <p className="mt-2 max-w-2xl text-base text-slate-300">You’re signed in and ready to find courses that match your goals.</p>
      <button className="mt-5 text-sm font-semibold text-cyan-200 underline underline-offset-4 hover:text-white" onClick={onDismiss}>Continue to Coursewise</button>
    </div>
  )
}

function emptyProfile() {
  return { learning_status: "", learning_level: "", learning_goal: "", skills: "" }
}

function profileFromUser(user) {
  return {
    learning_status: user.learning_status || "",
    learning_level: user.learning_level || "",
    learning_goal: user.learning_goal || "",
    skills: user.skills || "",
  }
}

export default App
