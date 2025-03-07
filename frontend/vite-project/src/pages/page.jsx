import { ParkingAnalyzer } from "@/components/parking-analyzer"

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            Parking Lot Analyzer
          </h1>
          <p className="mt-3 text-xl text-gray-500">
            Upload an image of a parking lot to analyze available spaces
          </p>
        </div>
        
        <ParkingAnalyzer />
      </div>
    </main>
  )
}
