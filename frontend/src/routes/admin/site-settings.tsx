import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  Globe,
  Mail,
  Plus,
  Save,
  Settings as SettingsIcon,
  Shield,
  Trash2,
} from "lucide-react"
import { useEffect, useState } from "react"

import { SettingsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/admin/site-settings")({
  component: SiteSettings,
  head: () => ({
    meta: [{ title: "Site Settings — Eagle Eye" }],
  }),
})

interface SettingPair {
  key: string
  value: string
  description?: string
}

function SiteSettings() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  // Standard settings states
  const [siteName, setSiteName] = useState("Eagle Eye")
  const [siteTagline, setSiteTagline] = useState("CDLB Media Club News Website")
  const [contactEmail, setContactEmail] = useState("mediaclub@cdlb.edu.ph")
  const [newsroomLocation, setNewsroomLocation] = useState("Colegio de Los Baños, Laguna")
  const [facebookUrl, setFacebookUrl] = useState("https://facebook.com/cdlbmediaclub")
  const [twitterUrl, setTwitterUrl] = useState("")
  const [instagramUrl, setInstagramUrl] = useState("")

  // Custom key-values
  const [customSettings, setCustomSettings] = useState<SettingPair[]>([])
  const [newKey, setNewKey] = useState("")
  const [newValue, setNewValue] = useState("")

  const { data: settingsRes, isLoading } = useQuery({
    queryKey: ["admin-site-settings"],
    queryFn: () => SettingsService.getSiteSettings(),
  })

  useEffect(() => {
    if (settingsRes) {
      const items: any[] =
        (settingsRes as any)?.data?.data || (settingsRes as any)?.data || []

      const map: Record<string, string> = {}
      const extra: SettingPair[] = []

      const knownKeys = [
        "site_name",
        "site_tagline",
        "contact_email",
        "newsroom_location",
        "facebook_url",
        "twitter_url",
        "instagram_url",
      ]

      items.forEach((item) => {
        map[item.key] = item.value
        if (!knownKeys.includes(item.key)) {
          extra.push({
            key: item.key,
            value: item.value,
            description: item.description,
          })
        }
      })

      if (map["site_name"] !== undefined) setSiteName(map["site_name"])
      if (map["site_tagline"] !== undefined) setSiteTagline(map["site_tagline"])
      if (map["contact_email"] !== undefined) setContactEmail(map["contact_email"])
      if (map["newsroom_location"] !== undefined) setNewsroomLocation(map["newsroom_location"])
      if (map["facebook_url"] !== undefined) setFacebookUrl(map["facebook_url"])
      if (map["twitter_url"] !== undefined) setTwitterUrl(map["twitter_url"])
      if (map["instagram_url"] !== undefined) setInstagramUrl(map["instagram_url"])

      setCustomSettings(extra)
    }
  }, [settingsRes])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const allToSave: SettingPair[] = [
        { key: "site_name", value: siteName, description: "Website brand name" },
        { key: "site_tagline", value: siteTagline, description: "Website tagline" },
        { key: "contact_email", value: contactEmail, description: "Official contact email" },
        { key: "newsroom_location", value: newsroomLocation, description: "Physical newsroom location" },
        { key: "facebook_url", value: facebookUrl, description: "Facebook page URL" },
        { key: "twitter_url", value: twitterUrl, description: "Twitter/X URL" },
        { key: "instagram_url", value: instagramUrl, description: "Instagram page URL" },
        ...customSettings,
      ]

      for (const item of allToSave) {
        if (item.key) {
          await SettingsService.setSiteSetting({
            body: {
              key: item.key,
              value: item.value,
            },
          })
        }
      }
    },
    onSuccess: () => {
      showSuccessToast("Site settings saved successfully!")
      queryClient.invalidateQueries({ queryKey: ["admin-site-settings"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to save settings")
    },
  })

  const handleAddCustom = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKey.trim()) return
    setCustomSettings((prev) => [
      ...prev,
      { key: newKey.trim().toLowerCase().replace(/\s+/g, "_"), value: newValue },
    ])
    setNewKey("")
    setNewValue("")
  }

  const handleRemoveCustom = (key: string) => {
    setCustomSettings((prev) => prev.filter((s) => s.key !== key))
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Site Settings</h1>
          <p className="text-muted-foreground text-sm">
            Configure global website identity, contact info, and social links.
          </p>
        </div>
        <LoadingButton
          loading={saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
          className="gap-2"
        >
          <Save className="size-4" />
          Save All Settings
        </LoadingButton>
      </div>

      {isLoading ? (
        <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground">
          Loading site settings...
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* General Brand Settings */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Globe className="size-5 text-primary" />
                <CardTitle className="text-lg">Brand & Identity</CardTitle>
              </div>
              <CardDescription>
                Public title, tagline, and header branding for Eagle Eye.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="siteName">Publication Name</Label>
                  <Input
                    id="siteName"
                    value={siteName}
                    onChange={(e) => setSiteName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="siteTagline">Tagline</Label>
                  <Input
                    id="siteTagline"
                    value={siteTagline}
                    onChange={(e) => setSiteTagline(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Contact & Location */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Mail className="size-5 text-primary" />
                <CardTitle className="text-lg">Contact & Location</CardTitle>
              </div>
              <CardDescription>
                Display details on the Contact Us page and footer.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="contactEmail">Official Email</Label>
                  <Input
                    id="contactEmail"
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newsroomLocation">Newsroom Location</Label>
                  <Input
                    id="newsroomLocation"
                    value={newsroomLocation}
                    onChange={(e) => setNewsroomLocation(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Social Links */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Shield className="size-5 text-primary" />
                <CardTitle className="text-lg">Social Media Links</CardTitle>
              </div>
              <CardDescription>
                Links shown on the footer and article share buttons.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="fb">Facebook Page URL</Label>
                  <Input
                    id="fb"
                    value={facebookUrl}
                    onChange={(e) => setFacebookUrl(e.target.value)}
                    placeholder="https://facebook.com/..."
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tw">Twitter / X URL</Label>
                  <Input
                    id="tw"
                    value={twitterUrl}
                    onChange={(e) => setTwitterUrl(e.target.value)}
                    placeholder="https://x.com/..."
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ig">Instagram URL</Label>
                  <Input
                    id="ig"
                    value={instagramUrl}
                    onChange={(e) => setInstagramUrl(e.target.value)}
                    placeholder="https://instagram.com/..."
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Custom Settings Key/Value */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <SettingsIcon className="size-5 text-primary" />
                <CardTitle className="text-lg">Advanced / Custom Settings</CardTitle>
              </div>
              <CardDescription>
                Arbitrary key-value config options for site features.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {customSettings.map((item, idx) => (
                <div key={item.key} className="flex items-center gap-3">
                  <Input
                    value={item.key}
                    disabled
                    className="w-1/3 font-mono text-xs"
                  />
                  <Input
                    value={item.value}
                    onChange={(e) => {
                      const val = e.target.value
                      setCustomSettings((prev) =>
                        prev.map((s, i) => (i === idx ? { ...s, value: val } : s)),
                      )
                    }}
                    className="flex-1 text-sm"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveCustom(item.key)}
                    className="text-destructive hover:text-destructive shrink-0 size-8"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              ))}

              <form onSubmit={handleAddCustom} className="flex items-center gap-3 pt-2">
                <Input
                  placeholder="key_name"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  className="w-1/3 font-mono text-xs"
                />
                <Input
                  placeholder="value"
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  className="flex-1 text-sm"
                />
                <Button
                  type="submit"
                  variant="outline"
                  size="sm"
                  disabled={!newKey.trim()}
                  className="gap-1 shrink-0"
                >
                  <Plus className="size-4" /> Add
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
