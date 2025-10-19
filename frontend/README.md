# Poly Boost Frontend

A React-based dashboard for monitoring and managing Polymarket copy trading operations.

## Features

- **Market Overview**: View market statistics and recent trading activity
- **Traders Dashboard**: Monitor trader positions, orders, and activity history
  - Select from configured wallets
  - View real-time positions
  - Track order history
  - Review activity timeline

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Ant Design** - UI component library
- **React Router** - Client-side routing
- **Axios** - HTTP client

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

## Installation

```bash
# Install dependencies
npm install
```

## Configuration

Create a `.env.local` file in the project root:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client
│   │   └── client.ts     # Backend API integration
│   ├── components/       # Reusable components
│   │   ├── PositionList.tsx
│   │   ├── OrderList.tsx
│   │   └── ActivityList.tsx
│   ├── layouts/          # Layout components
│   │   └── MainLayout.tsx
│   ├── pages/            # Page components
│   │   ├── Market/
│   │   │   └── index.tsx
│   │   └── Traders/
│   │       └── index.tsx
│   ├── types/            # TypeScript type definitions
│   │   └── index.ts
│   ├── config.ts         # App configuration
│   ├── App.tsx           # Main app component
│   └── main.tsx          # Entry point
├── public/               # Static assets
├── index.html            # HTML template
└── package.json          # Dependencies
```

## API Integration

The frontend communicates with the backend API:

- `GET /config/wallets` - Get configured wallets
- `GET /positions/{wallet}` - Get wallet positions
- `GET /wallets/{wallet}/balance` - Get wallet balance
- `GET /trading/status` - Get trading status
- `GET /trading/traders` - List all traders

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Usage

1. **Start the backend API** (see main README)
2. **Start the frontend development server**:
   ```bash
   npm run dev
   ```
3. **Open your browser** to `http://localhost:5173`
4. **Navigate between pages**:
   - Market: View overall market statistics
   - Traders: Select a wallet and view its positions, orders, and activity

## Features by Page

### Market Page
- Active traders count
- Total trading volume
- 24-hour price changes
- Recent activity table

### Traders Page
- Wallet selector (from config.yaml)
- Wallet statistics (balance, total value, position count)
- Tabbed interface:
  - **Positions**: Current open positions with P&L
  - **Orders**: Order history with status
  - **Activities**: Complete activity timeline

## Troubleshooting

### API Connection Issues

If you see "Failed to load wallet data" errors:
1. Verify backend API is running on port 8000
2. Check CORS settings in backend
3. Verify `VITE_API_BASE_URL` in `.env.local`

### Build Issues

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Development Notes

- The app uses Ant Design's default theme with primary color `#1890ff`
- All API calls include error handling with user-friendly messages
- Position data is refreshed when wallet selection changes
- TypeScript strict mode is enabled for type safety
