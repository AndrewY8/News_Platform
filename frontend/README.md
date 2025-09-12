# Marathon News Frontend

A modern, modular React/Next.js frontend for the Marathon News application, featuring AI-powered news personalization and real-time market data.

## 🏗️ Architecture

### **Component Structure**
```
frontend/
├── app/
│   ├── app.tsx          # Main application component
│   ├── page.tsx         # Entry point
│   └── globals.css      # Global styles
├── components/
│   ├── Sidebar.tsx      # Navigation, chat, and ticker management
│   ├── NewsFeed.tsx     # News display and interaction
│   └── ui/              # Reusable UI components (shadcn/ui)
├── services/
│   └── api.ts           # Backend API communication
├── types/
│   └── index.ts         # TypeScript type definitions
└── lib/
    └── utils.ts         # Utility functions
```

### **Key Features**
- **Modular Design**: Clean separation of concerns with reusable components
- **Type Safety**: Full TypeScript support with proper interfaces
- **Real-time Data**: Live market data and news updates
- **AI Integration**: Gemini-powered news personalization and chat
- **Responsive UI**: Modern design with Tailwind CSS

## 🚀 Getting Started

### **Prerequisites**
- Node.js 18+
- npm or yarn
- Backend server running on port 8004

### **Installation**
```bash
cd frontend

# Install dependencies
npm install

# Create environment file
cp env.example .env.local

# Start development server
npm run dev
```

### **Environment Variables**
Create `.env.local` with:
```env
NEXT_PUBLIC_API_URL=http://localhost:8004
```

## 🔧 Development

### **Component Development**
- **Sidebar**: Handles navigation, chat, and ticker management
- **NewsFeed**: Displays news articles with sentiment analysis
- **API Service**: Centralized backend communication

### **State Management**
- Uses React hooks for local state
- Props for component communication
- API calls for data persistence

### **Styling**
- Tailwind CSS for utility-first styling
- shadcn/ui components for consistent design
- Responsive design with mobile considerations

## 📱 Features

### **News Management**
- **Top News**: General financial news feed
- **Personalized Feed**: AI-filtered news based on user tickers
- **Saved News**: Bookmarked articles
- **Search**: AI-powered news search via chat

### **Ticker Management**
- Add/remove stock tickers
- Real-time market data
- Time period selection (1D, 1W, 1M, 3M, 1Y)

### **AI Chat (News Runner)**
- Ask questions about investments
- Get personalized news recommendations
- Powered by Gemini AI
- Context-aware responses

### **Article Interactions**
- Save/unsave articles
- Click tracking for analytics
- Sentiment analysis display
- Relevance scoring

## 🔌 API Integration

### **Backend Endpoints**
- `/api/articles` - News fetching
- `/api/market/*` - Market data
- `/api/user` - User preferences
- `/api/chat` - AI chat interface

### **Data Flow**
1. **Initialization**: Load user profile and tickers
2. **News Fetching**: Get articles based on active tab
3. **Real-time Updates**: Market data and news refresh
4. **User Interactions**: Save, click, and chat actions

## 🎨 Design System

### **Color Palette**
- **Primary**: Blue (#2563eb)
- **Success**: Green (#16a34a)
- **Error**: Red (#dc2626)
- **Neutral**: Gray scale (#f9fafb to #111827)

### **Typography**
- **Headings**: Large, bold with tracking
- **Body**: Small, readable text
- **Monospace**: For ticker symbols and data

### **Layout**
- **Fixed Header**: Large "MARATHON" branding
- **Sidebar**: Navigation and controls
- **Main Content**: News feed with responsive design

## 🧪 Testing

### **Component Testing**
```bash
# Run tests
npm test

# Test specific component
npm test -- --testNamePattern="Sidebar"
```

### **API Testing**
- Mock API responses for development
- Error handling for network issues
- Fallback data when services unavailable

## 🚀 Deployment

### **Build Process**
```bash
# Production build
npm run build

# Start production server
npm start
```

### **Environment Configuration**
- Set `NEXT_PUBLIC_API_URL` for production backend
- Configure CORS settings
- Set up proper error monitoring

## 🔮 Future Enhancements

### **Planned Features**
- **Real-time Notifications**: Breaking news alerts
- **Advanced Analytics**: User engagement metrics
- **Portfolio Integration**: Connect to trading accounts
- **Social Features**: Share and discuss articles

### **Technical Improvements**
- **State Management**: Redux or Zustand for complex state
- **Caching**: React Query for API data caching
- **PWA**: Progressive web app capabilities
- **Offline Support**: Service worker for offline reading

## 🐛 Troubleshooting

### **Common Issues**
1. **API Connection**: Check backend server and CORS settings
2. **Type Errors**: Ensure all components have proper TypeScript types
3. **Styling Issues**: Verify Tailwind CSS configuration
4. **Build Errors**: Check Node.js version and dependency conflicts

### **Debug Mode**
```bash
# Enable debug logging
DEBUG=* npm run dev
```

## 📚 Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

## 🤝 Contributing

1. Follow the existing component structure
2. Add proper TypeScript types
3. Include error handling
4. Test with different screen sizes
5. Update documentation

---

**Marathon News** - Delivering financial intelligence at the speed of thought.
