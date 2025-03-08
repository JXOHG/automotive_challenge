export default function AboutPage() {
  return (
    <main className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold tracking-tight">About Parking Lot Analyzer</h1>
        </div>
        
        <div className="bg-card text-card-foreground rounded-lg border shadow-sm p-6">
          <h2 className="text-2xl font-semibold mb-4">How It Works</h2>
          <p className="mb-4">
            The Parking Lot Analyzer uses a convolutional neural network (CNN) to analyze images of parking lots and determine which spaces are occupied and which are available.
          </p>
          
          <h2 className="text-2xl font-semibold mb-4 mt-8">Technology</h2>
          <p className="mb-2">
            Our system is built using:
          </p>
          <ul className="list-disc list-inside space-y-2 mb-6 ml-4 text-muted-foreground">
            <li>Next.js for the frontend interface</li>
            <li>Convolutional Neural Networks for image analysis</li>
            <li>Computer vision techniques for parking space detection</li>
          </ul>
          
          <h2 className="text-2xl font-semibold mb-4 mt-8">Accuracy</h2>
          <p>
            The system has been trained on thousands of parking lot images and achieves an accuracy of over 95% in detecting available and occupied spaces under various lighting and weather conditions.
          </p>
        </div>
      </div>
    </main>
  )
}
