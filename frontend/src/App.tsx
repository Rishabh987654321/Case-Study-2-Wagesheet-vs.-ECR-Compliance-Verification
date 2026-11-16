import { Navigate, Route, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { HistoryPage } from "./routes/HistoryPage"
import { ResultsPage } from "./routes/ResultsPage"
import { UploadPage } from "./routes/UploadPage"

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/upload" replace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/verify/:id" element={<ResultsPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
    </Routes>
  )
}
