import { HeroGrid } from "@/components/layout/hero-grid";

export default function Home() {
  return (
    <section className="py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl font-extrabold mb-4">Hate to Action</h1>
          <p className="text-lg text-gray-600">
            This project, “Hate-2-Action,” is a sophisticated, full-stack application designed to analyze user messages, identify underlying social and psychological problems, and recommend relevant projects that can help address those issues. The system leverages a powerful combination of a machine learning pipeline, a modern web interface, and a Telegram bot to provide a seamless and intuitive user experience.
          </p>
        </div>
        <div className="mt-12">
          <HeroGrid />
        </div>
      </div>
    </section>
  )
}
