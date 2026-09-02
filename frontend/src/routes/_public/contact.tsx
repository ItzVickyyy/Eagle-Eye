import { zodResolver } from "@hookform/resolvers/zod"
import { createFileRoute } from "@tanstack/react-router"
import { Mail, MapPin, Send } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_public/contact")({
  component: ContactPage,
  head: () => ({
    meta: [{ title: "Contact Us - Eagle Eye" }],
  }),
})

const contactSchema = z.object({
  name: z.string().min(2, { message: "Please enter your name" }),
  email: z.email({ message: "Invalid email address" }),
  subject: z.string().min(3, { message: "Please add a short subject" }),
  message: z
    .string()
    .min(10, { message: "Message should be at least 10 characters" }),
})

type ContactFormData = z.infer<typeof contactSchema>

function ContactPage() {
  const { showSuccessToast } = useCustomToast()
  const form = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
    mode: "onBlur",
    defaultValues: { name: "", email: "", subject: "", message: "" },
  })

  // NOTE: There is no `/contact` submission endpoint on the backend yet.
  // Rather than fake a network call, this simply confirms the message was
  // validated and points the person to email in the meantime.
  // TODO(api): replace with a real mutation once ContactService exists,
  // e.g. ContactService.sendMessage({ body: data }).
  const onSubmit = (_data: ContactFormData) => {
    showSuccessToast(
      "Thanks! Our contact form isn't wired up to email yet — please reach us directly at eagleeye@cdlb.edu.ph in the meantime.",
    )
    form.reset()
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="text-center">
        <h1 className="font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Contact Us
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-muted-foreground">
          Got a story tip, correction, or question for the Eagle Eye staff? We'd
          love to hear from you.
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <div className="rounded-xl border bg-card p-6">
            <h2 className="font-semibold text-foreground">Newsroom Contact</h2>
            <ul className="mt-4 space-y-4 text-sm">
              <li className="flex items-start gap-3">
                <Mail className="mt-0.5 size-4 shrink-0 text-primary" />
                <div>
                  <p className="font-medium text-foreground">Email</p>
                  <a
                    href="mailto:eagleeye@cdlb.edu.ph"
                    className="text-muted-foreground hover:text-foreground"
                  >
                    eagleeye@cdlb.edu.ph
                  </a>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <MapPin className="mt-0.5 size-4 shrink-0 text-primary" />
                <div>
                  <p className="font-medium text-foreground">Media Club Room</p>
                  <p className="text-muted-foreground">
                    Colegio de los Baños
                    <br />
                    Los Baños, Laguna, Philippines
                  </p>
                </div>
              </li>
            </ul>
            <p className="mt-6 text-xs text-muted-foreground">
              Have a story tip? Include as much detail as you can — dates,
              names, and where it happened help us follow up faster.
            </p>
          </div>
        </div>

        <div className="lg:col-span-3">
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-5 rounded-xl border bg-card p-6"
            >
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Juan Dela Cruz" {...field} />
                      </FormControl>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email</FormLabel>
                      <FormControl>
                        <Input
                          type="email"
                          placeholder="you@example.com"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="subject"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Subject</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Story tip, correction, etc."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="message"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Message</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Tell us more…"
                        rows={5}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />

              <LoadingButton
                type="submit"
                loading={form.formState.isSubmitting}
                className="gap-1.5"
              >
                <Send className="size-4" />
                Send Message
              </LoadingButton>
              <p className="text-xs text-muted-foreground">
                This form isn't connected to email yet — for now, reach us
                directly at{" "}
                <a
                  href="mailto:eagleeye@cdlb.edu.ph"
                  className="underline underline-offset-2 hover:text-foreground"
                >
                  eagleeye@cdlb.edu.ph
                </a>
                .
              </p>
            </form>
          </Form>
        </div>
      </div>
    </div>
  )
}
