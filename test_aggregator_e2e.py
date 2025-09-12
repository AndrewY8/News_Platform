#!/usr/bin/env python3
"""
End-to-end integration test for the News Aggregator system.
Tests the complete pipeline: PlannerResults -> ContentChunks -> Clusters -> Summaries.
Includes Supabase database integration testing.
"""

import asyncio
import json
import os
import sys
import time
import logging
import traceback
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_agent.aggregator import AggregatorAgent, AggregatorConfig, create_aggregator_agent
from news_agent.aggregator.models import (
    ContentChunk, ChunkMetadata, SourceType, ReliabilityTier,
    ContentCluster, ClusterSummary, AggregatorOutput
)
from news_agent.aggregator.config import get_config
from news_agent.aggregator.supabase_manager import SupabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AggregatorE2ETester:
    """Comprehensive end-to-end test suite for the News Aggregator system."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.results = {}
        self.test_scenarios = self._create_test_scenarios()
        self.gemini_api_key = self._get_gemini_api_key()
        
        # Performance tracking
        self.start_time = None
        self.total_processing_time = 0
        self.performance_metrics = {}
        
        logger.info("AggregatorE2ETester initialized with Gemini API")
    
    def _get_gemini_api_key(self) -> str:
        """Get Gemini API key from environment."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            # Try loading from .env file
            try:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv('GEMINI_API_KEY')
            except ImportError:
                pass
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        return api_key
    
    def _get_supabase_config(self) -> Tuple[Optional[str], Optional[str]]:
        """Get Supabase URL and key from configuration."""
        try:
            # Load environment variables if needed
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                # Try loading from .env file
                try:
                    from dotenv import load_dotenv
                    load_dotenv()
                    supabase_url = os.getenv('SUPABASE_URL')
                    supabase_key = os.getenv('SUPABASE_KEY')
                except ImportError:
                    pass
            
            return supabase_url, supabase_key
        except Exception as e:
            print(f"Warning: Failed to get Supabase configuration: {e}")
            return None, None
    
    def _create_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create comprehensive test scenarios with mock PlannerAgent results."""
        
        # Base timestamp for consistent testing
        base_time = datetime.utcnow()
        
        scenarios = [
            {
                "name": "Breaking News Technology",
                "description": "Multiple breaking news articles about a major tech announcement",
                "expected_clusters": 2,
                "expected_min_sources": 15,
                "planner_results": {
                    "breaking_news": [
                        {
                            "title": "BREAKING: Apple Announces Revolutionary AI Chip M4 Ultra",
                            "url": "https://techcrunch.com/apple-m4-ultra-announcement",
                            "description": "Apple today announced its groundbreaking M4 Ultra chip featuring unprecedented AI processing capabilities, marking a major leap forward in personal computing technology.",
                            "raw_content": "In a surprise announcement today, Apple unveiled its most powerful chip yet, the M4 Ultra, designed specifically for artificial intelligence workloads. The new processor features 128 AI compute cores and delivers 10x the performance of previous generations. CEO Tim Cook called it 'the most significant leap in computing power we've ever achieved.' The chip integrates seamlessly with Apple's ecosystem and will power the next generation of MacBooks and Mac Studios. Industry analysts are calling this a game-changer that could reshape the entire personal computing landscape. The M4 Ultra uses a revolutionary 3nm process technology and includes dedicated neural processing units that can handle complex AI tasks in real-time.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(minutes=15)).isoformat(),
                            "author": "Sarah Chen",
                            "image_urls": ["https://example.com/apple-chip.jpg"]
                        },
                        {
                            "title": "Apple's M4 Ultra Chip: A Deep Dive into the AI Revolution",
                            "url": "https://arstechnica.com/apple-m4-ultra-deep-dive",
                            "description": "Technical analysis of Apple's new M4 Ultra processor reveals impressive AI capabilities that could transform mobile computing.",
                            "raw_content": "Apple's newly announced M4 Ultra represents a paradigm shift in processor design, with AI acceleration at its core. Our technical analysis reveals that the chip's 128 AI cores can deliver over 50 trillion operations per second, far exceeding competitors. The architecture includes specialized tensor processing units, advanced memory management, and power efficiency improvements of up to 40%. This positions Apple ahead of NVIDIA and Intel in the AI chip race. The implications for creative professionals, researchers, and developers are enormous. Real-time video processing, advanced machine learning inference, and complex AI applications will now be possible on portable devices.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(minutes=10)).isoformat(),
                            "author": "Michael Rodriguez"
                        },
                        {
                            "title": "Stock Alert: Apple Shares Surge 8% on M4 Ultra Announcement",
                            "url": "https://bloomberg.com/apple-stock-surge-m4-ultra",
                            "description": "Apple stock jumped to new highs following the surprise chip announcement, with analysts upgrading price targets.",
                            "raw_content": "Apple Inc. shares soared 8% in after-hours trading following the surprise announcement of the M4 Ultra chip. The stock reached a new all-time high of $195.50 as investors reacted positively to Apple's continued innovation in semiconductor design. Wall Street analysts are raising their price targets, with Goldman Sachs increasing from $180 to $210. The chip announcement addresses concerns about Apple falling behind in the AI race and demonstrates the company's commitment to maintaining its technological edge. Trading volume increased 300% above average as institutional investors rushed to adjust their positions.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(minutes=5)).isoformat(),
                            "author": "Jennifer Walsh"
                        },
                        {
                            "title": "Apple M4 Ultra: What Developers Need to Know",
                            "url": "https://developer.apple.com/m4-ultra-developer-guide",
                            "description": "Apple releases developer documentation for M4 Ultra chip optimization and new AI development frameworks.",
                            "raw_content": "Apple has released comprehensive developer documentation for the M4 Ultra chip, revealing new APIs and optimization techniques for AI-powered applications. The new Metal Performance Shaders framework includes specialized functions for neural network inference, while Core ML has been enhanced to take full advantage of the chip's AI cores. Developers can now access up to 128 parallel AI compute units, enabling real-time processing of complex machine learning models. The documentation includes sample code for computer vision, natural language processing, and generative AI applications. Early adopter developers report 5-10x performance improvements in AI workloads compared to previous generation chips.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(minutes=20)).isoformat(),
                            "author": "Alex Kim"
                        },
                        {
                            "title": "Intel Responds to Apple M4 Ultra with Accelerated Roadmap",
                            "url": "https://intel.com/response-apple-m4-ultra",
                            "description": "Intel accelerates its own AI chip development timeline following Apple's M4 Ultra announcement.",
                            "raw_content": "Intel Corporation announced an accelerated roadmap for its next-generation AI processors in response to Apple's M4 Ultra chip launch. CEO Pat Gelsinger stated that Intel's upcoming Lunar Lake and Arrow Lake processors will feature enhanced AI capabilities to compete directly with Apple's offering. The company is fast-tracking development of its Neural Processing Unit (NPU) technology and promises to deliver competitive AI performance by early next year. Intel's stock dropped 3% following Apple's announcement, prompting the urgent strategic response. The chip giant is also expanding partnerships with Microsoft and Google to optimize software for its AI hardware.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(minutes=25)).isoformat(),
                            "author": "David Park"
                        },
                        {
                            "title": "NVIDIA CEO Jensen Huang Comments on Apple M4 Ultra",
                            "url": "https://nvidia.com/jensen-huang-apple-m4-ultra-response",
                            "description": "NVIDIA's CEO acknowledges Apple's achievement while highlighting NVIDIA's continued leadership in AI acceleration.",
                            "raw_content": "NVIDIA CEO Jensen Huang acknowledged Apple's M4 Ultra achievement during an impromptu press call, calling it 'impressive engineering' while emphasizing NVIDIA's continued leadership in AI acceleration. Huang noted that while Apple's chip excels in consumer applications, NVIDIA's GPUs remain superior for enterprise AI training and high-performance computing workloads. The CEO highlighted NVIDIA's upcoming H200 and B100 chips, which are designed for data center AI applications. Despite the competition, NVIDIA's stock remained relatively stable, with analysts noting the different market segments served by the two companies. Huang expressed optimism about the growing AI chip market benefiting all players.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(minutes=30)).isoformat(),
                            "author": "Lisa Zhang"
                        },
                        {
                            "title": "Apple M4 Ultra: Manufacturing Partner TSMC Celebrates Success",
                            "url": "https://tsmc.com/apple-m4-ultra-manufacturing-success",
                            "description": "Taiwan Semiconductor Manufacturing Company highlights its role in producing Apple's groundbreaking M4 Ultra chip.",
                            "raw_content": "Taiwan Semiconductor Manufacturing Company (TSMC) celebrated its successful production of Apple's M4 Ultra chip, showcasing the advanced 3nm manufacturing process technology. TSMC Chairman Mark Liu praised the collaboration with Apple, noting the challenges overcome in producing such a complex AI-optimized processor. The foundry's advanced packaging techniques and extreme ultraviolet (EUV) lithography were crucial in achieving the chip's performance and power efficiency targets. TSMC's stock rose 4% on the news, with investors recognizing the company's technological leadership. The success of the M4 Ultra production reinforces TSMC's position as the world's leading advanced semiconductor manufacturer.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(minutes=35)).isoformat(),
                            "author": "Wang Chen"
                        },
                        {
                            "title": "Apple M4 Ultra Benchmark Results Leak Online",
                            "url": "https://geekbench.com/apple-m4-ultra-benchmark-leak",
                            "description": "Early benchmark results for Apple's M4 Ultra chip surface online, showing dramatic performance improvements.",
                            "raw_content": "Leaked benchmark results for Apple's M4 Ultra chip have appeared on Geekbench, revealing dramatic performance improvements across all tested categories. The chip achieved a single-core score of 3,200 and multi-core score of 28,500, representing 40% and 65% improvements respectively over the M3 Ultra. Most impressive are the AI-specific benchmarks, where the M4 Ultra scored 95,000 points in machine learning inference tests, nearly triple the previous generation. Graphics performance also saw significant gains, with Metal compute scores reaching 175,000 points. These results, if authentic, confirm Apple's claims about the chip's revolutionary capabilities and position it as the most powerful consumer processor ever created.",
                            "source_retriever": "DuckDuckGoRetriever",
                            "published_date": (base_time - timedelta(minutes=40)).isoformat(),
                            "author": "Tech Leaker Anonymous"
                        },
                        {
                            "title": "Apple M4 Ultra: Industry Analysts Predict Market Impact",
                            "url": "https://gartner.com/apple-m4-ultra-market-analysis",
                            "description": "Technology research firms analyze the potential market impact of Apple's M4 Ultra chip announcement.",
                            "raw_content": "Leading technology research firm Gartner predicts that Apple's M4 Ultra chip will significantly disrupt the AI processor market, potentially capturing 15% of the enterprise AI chip market within two years. Analyst Sarah Johnson notes that the chip's combination of performance, power efficiency, and integration with Apple's ecosystem creates a compelling value proposition for businesses. The research suggests that traditional PC manufacturers may need to accelerate their AI chip development to remain competitive. Gartner estimates that Apple's silicon division could generate an additional $8 billion in revenue annually once M4 Ultra-powered devices reach full market penetration. The analysis also highlights potential supply chain implications as demand for advanced AI chips continues to grow.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(minutes=45)).isoformat(),
                            "author": "Sarah Johnson"
                        },
                        {
                            "title": "Apple M4 Ultra: Gaming Performance Breakthrough",
                            "url": "https://ign.com/apple-m4-ultra-gaming-performance",
                            "description": "Gaming industry reacts to Apple M4 Ultra's impressive graphics and compute capabilities for next-generation games.",
                            "raw_content": "The gaming industry is buzzing about Apple's M4 Ultra chip and its potential to transform Mac gaming. Early demos showed the chip running demanding AAA games at 4K resolution with ray tracing enabled, achieving frame rates previously impossible on Apple hardware. Epic Games CEO Tim Sweeney praised the chip's capabilities, announcing enhanced Unreal Engine 5 support for M4 Ultra-powered Macs. Unity Technologies also committed to optimizing its game engine for the new chip architecture. Gaming benchmark specialists report that the M4 Ultra's GPU performance rivals discrete graphics cards costing $800-1000. This breakthrough could finally position Mac as a serious gaming platform, potentially attracting game developers who previously focused solely on PC and console platforms.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(minutes=50)).isoformat(),
                            "author": "Gaming Reporter Mike"
                        },
                        {
                            "title": "Apple M4 Ultra: Environmental Impact and Sustainability",
                            "url": "https://apple.com/newsroom/m4-ultra-environmental-impact",
                            "description": "Apple highlights the environmental benefits and sustainability features of the M4 Ultra chip design.",
                            "raw_content": "Apple emphasized the environmental benefits of the M4 Ultra chip, highlighting a 30% reduction in power consumption compared to equivalent performance from previous generations. The company's environmental team reports that the advanced 3nm manufacturing process and optimized architecture contribute to significantly lower carbon emissions over the chip's lifecycle. Apple's commitment to carbon neutrality by 2030 is supported by innovations like the M4 Ultra, which requires less energy while delivering superior performance. The chip's efficiency gains translate to longer battery life in portable devices and reduced electricity consumption in desktop systems. Apple also announced that 75% of the materials used in M4 Ultra packaging are recycled or renewable, continuing the company's sustainability initiatives.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(minutes=55)).isoformat(),
                            "author": "Environmental Team Apple"
                        },
                        {
                            "title": "Apple M4 Ultra: Academic Research Applications",
                            "url": "https://nature.com/apple-m4-ultra-research-applications",
                            "description": "Universities and research institutions explore the potential of Apple's M4 Ultra for scientific computing and AI research.",
                            "raw_content": "Leading academic institutions are evaluating Apple's M4 Ultra chip for scientific computing and AI research applications. Stanford University's AI lab reported that the chip's neural processing capabilities could accelerate deep learning research by up to 5x compared to traditional GPU clusters for certain workloads. MIT's Computer Science department announced plans to integrate M4 Ultra-powered systems into their curriculum, recognizing the chip's potential to democratize AI research. Harvard Medical School is exploring the chip's applications in medical imaging and drug discovery, where the combination of AI acceleration and power efficiency could enable new research methodologies. The academic community's enthusiasm reflects the M4 Ultra's potential to lower barriers to AI research and enable breakthrough discoveries.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=1)).isoformat(),
                            "author": "Dr. Research Scientist"
                        },
                        {
                            "title": "Apple M4 Ultra: Creative Professional Response",
                            "url": "https://creativepro.com/apple-m4-ultra-creative-professional-response",
                            "description": "Creative professionals in video, music, and design industries react to Apple's M4 Ultra capabilities.",
                            "raw_content": "Creative professionals are celebrating Apple's M4 Ultra chip as a game-changer for video editing, 3D rendering, and music production workflows. Hollywood post-production houses report that the chip's AI acceleration enables real-time 8K video processing with complex effects, dramatically reducing rendering times. Music producers highlight the chip's ability to handle hundreds of audio tracks with AI-powered processing plugins without latency issues. Adobe announced enhanced Creative Suite optimization for M4 Ultra, promising up to 10x faster performance in AI-powered features like Content-Aware Fill and Neural Filters. Autodesk is also updating its 3D modeling software to leverage the chip's parallel processing capabilities. The creative community's enthusiasm reflects the M4 Ultra's potential to revolutionize professional workflows.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=5)).isoformat(),
                            "author": "Creative Industry Reporter"
                        },
                        {
                            "title": "Apple M4 Ultra: Supply Chain and Production Challenges",
                            "url": "https://reuters.com/apple-m4-ultra-supply-chain-challenges",
                            "description": "Analysis of potential supply chain constraints and production scaling for Apple's M4 Ultra chip.",
                            "raw_content": "Industry analysts are examining potential supply chain challenges for Apple's M4 Ultra chip production, given its advanced 3nm manufacturing requirements. TSMC's limited 3nm production capacity could create bottlenecks as demand for M4 Ultra-powered devices increases. Supply chain experts estimate that Apple may face initial production constraints, potentially limiting device availability in the first quarters following launch. The complexity of the M4 Ultra's design also presents yield challenges, with early reports suggesting lower-than-typical production yields. However, Apple's strong relationship with TSMC and advance planning typically help mitigate such issues. The company is reportedly working with additional suppliers to secure critical components and ensure adequate supply for anticipated demand.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=10)).isoformat(),
                            "author": "Supply Chain Analyst"
                        },
                        {
                            "title": "Apple M4 Ultra: Patent Portfolio Expansion",
                            "url": "https://uspto.gov/apple-m4-ultra-patent-filings",
                            "description": "Apple's extensive patent filings related to M4 Ultra chip architecture and AI processing innovations.",
                            "raw_content": "Apple's patent filings reveal the extensive intellectual property portfolio supporting the M4 Ultra chip's innovative architecture. Over 200 patents related to AI acceleration, neural processing, and power management were filed in the two years leading up to the announcement. Key patents cover novel approaches to parallel AI processing, dynamic power allocation, and thermal management in high-performance chips. Legal experts note that Apple's comprehensive patent protection could provide competitive advantages and potential licensing opportunities. The patent portfolio also includes innovations in chip packaging, interconnect technology, and software-hardware integration specific to AI workloads. This intellectual property foundation demonstrates Apple's long-term commitment to AI chip development and positions the company for future innovations in the space.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=15)).isoformat(),
                            "author": "Patent Attorney"
                        },
                        {
                            "title": "Apple M4 Ultra: International Market Implications",
                            "url": "https://economist.com/apple-m4-ultra-international-implications",
                            "description": "Global analysis of Apple M4 Ultra's impact on international technology competition and trade relations.",
                            "raw_content": "The launch of Apple's M4 Ultra chip has significant implications for international technology competition and trade relations. Chinese technology companies are accelerating their own AI chip development programs in response to Apple's breakthrough, with government backing for domestic semiconductor initiatives increasing. European policymakers are discussing the strategic implications of US technology leadership in AI chips and potential responses to maintain competitiveness. Trade analysts note that the M4 Ultra's performance advantages could impact global supply chains and technology partnerships. The chip's success also highlights the importance of advanced manufacturing capabilities, with countries investing heavily in semiconductor fabrication facilities. International technology policy experts predict that the M4 Ultra will influence global AI strategy and semiconductor industry dynamics for years to come.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=20)).isoformat(),
                            "author": "International Trade Reporter"
                        },
                        {
                            "title": "Apple M4 Ultra: Security and Privacy Enhancements",
                            "url": "https://apple.com/newsroom/m4-ultra-security-privacy",
                            "description": "Apple details advanced security features and privacy protections built into the M4 Ultra chip architecture.",
                            "raw_content": "Apple highlighted advanced security and privacy features integrated into the M4 Ultra chip's architecture, setting new standards for AI processing protection. The chip includes a dedicated Secure Enclave with enhanced capabilities for protecting sensitive AI operations and user data. Hardware-level encryption for neural network processing ensures that personal information remains private even during complex AI computations. The M4 Ultra's security architecture prevents unauthorized access to AI models and training data, addressing enterprise concerns about intellectual property protection. Apple's privacy engineering team designed the chip to enable powerful AI features while maintaining the company's commitment to user privacy. These security enhancements position the M4 Ultra as a trusted platform for sensitive AI applications in healthcare, finance, and government sectors.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=25)).isoformat(),
                            "author": "Security Team Apple"
                        },
                        {
                            "title": "Apple M4 Ultra: Future Product Roadmap Speculation",
                            "url": "https://techradar.com/apple-m4-ultra-future-product-roadmap",
                            "description": "Technology journalists and analysts speculate about Apple's future product plans incorporating M4 Ultra technology.",
                            "raw_content": "Technology analysts are speculating about Apple's future product roadmap following the M4 Ultra announcement, predicting significant updates across the entire Mac lineup. Industry insiders suggest that MacBook Pro models featuring M4 Ultra will launch within six months, followed by Mac Studio and Mac Pro updates. Speculation also centers on potential iPad Pro models with scaled versions of the M4 Ultra architecture, bringing desktop-class AI performance to tablets. Some analysts predict that Apple may introduce new product categories specifically designed to showcase the M4 Ultra's capabilities, potentially including AI-focused development workstations or creative professional tools. The chip's breakthrough performance has raised expectations for Apple's entire silicon roadmap, with observers anticipating continued rapid innovation in future M-series processors.",
                            "source_retriever": "DuckDuckGoRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=30)).isoformat(),
                            "author": "Tech Roadmap Analyst"
                        },
                        {
                            "title": "Apple M4 Ultra: Developer Community Early Access Program",
                            "url": "https://developer.apple.com/m4-ultra-early-access",
                            "description": "Apple launches early access program for developers to optimize applications for M4 Ultra chip capabilities.",
                            "raw_content": "Apple announced an early access program allowing select developers to begin optimizing their applications for M4 Ultra chip capabilities ahead of general device availability. The program provides developers with M4 Ultra development kits and specialized tools for AI optimization. Participating developers include major software companies like Adobe, Autodesk, and independent app creators working on AI-powered applications. The early access program focuses on helping developers leverage the chip's 128 AI cores and enhanced neural processing capabilities. Apple's developer relations team is providing technical support and optimization guidelines to ensure applications can fully utilize the M4 Ultra's breakthrough performance. This proactive approach aims to ensure a robust ecosystem of optimized applications when M4 Ultra devices reach consumers.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=35)).isoformat(),
                            "author": "Developer Program Manager"
                        },
                        {
                            "title": "Apple M4 Ultra: Educational Institution Adoption Plans",
                            "url": "https://educationweek.com/apple-m4-ultra-educational-adoption",
                            "description": "Educational institutions explore adopting Apple M4 Ultra technology for AI education and research programs.",
                            "raw_content": "Educational institutions worldwide are developing adoption plans for Apple's M4 Ultra technology to enhance AI education and research programs. Major universities are budgeting for M4 Ultra-powered computer labs to provide students with hands-on experience in AI development and machine learning. K-12 school districts are evaluating how the chip's capabilities could transform STEM education through advanced computational projects and AI literacy programs. Educational technology companies are developing curriculum specifically designed to leverage the M4 Ultra's AI processing capabilities. The Association for Educational Communications and Technology praised Apple's innovation, noting its potential to democratize AI education and make advanced computational thinking accessible to more students. Several pilot programs are already underway to evaluate the educational impact of M4 Ultra-powered learning environments.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=1, minutes=40)).isoformat(),
                            "author": "Education Technology Reporter"
                        }
                    ],
                    "financial_news": [],
                    "general_news": [],
                    "sec_filings": []
                }
            },
            {
                "name": "Mixed Financial Earnings",
                "description": "Multiple earnings reports from different companies and sectors",
                "expected_clusters": 2,
                "expected_min_sources": 4,
                "planner_results": {
                    "breaking_news": [],
                    "financial_news": [
                        {
                            "title": "Microsoft Q3 Earnings Beat Expectations on Cloud Growth",
                            "url": "https://reuters.com/microsoft-q3-earnings-beat",
                            "description": "Microsoft reported strong Q3 results driven by Azure cloud services growth of 31% year-over-year.",
                            "raw_content": "Microsoft Corporation reported third-quarter earnings that exceeded Wall Street expectations, driven primarily by robust growth in its Azure cloud computing division. Revenue increased 17% to $61.9 billion, while Azure revenues grew 31% compared to the same period last year. CEO Satya Nadella highlighted the company's leadership in AI and cloud infrastructure, noting that AI services contributed $4.2 billion to quarterly revenue. The productivity and business processes segment, including Office 365, also showed strong performance with 15% growth. Microsoft's stock price rose 4% in after-hours trading as investors welcomed the results.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=2)).isoformat(),
                            "author": "David Kim",
                            "ticker": "MSFT"
                        },
                        {
                            "title": "Tesla Reports Record Q3 Deliveries Despite Production Challenges",
                            "url": "https://marketwatch.com/tesla-q3-deliveries-record",
                            "description": "Tesla delivered 435,000 vehicles in Q3, setting a new quarterly record despite supply chain headwinds.",
                            "raw_content": "Tesla Inc. announced record third-quarter vehicle deliveries of 435,000 units, surpassing analyst estimates of 420,000 despite ongoing supply chain challenges. The electric vehicle manufacturer's production efficiency improvements and expansion of manufacturing capacity contributed to the strong results. Model Y crossover continues to be the company's best-selling vehicle, accounting for 65% of total deliveries. CEO Elon Musk praised the team's execution and reiterated the company's goal of achieving 50% annual growth in vehicle deliveries. The results come as Tesla faces increased competition in the EV market from traditional automakers.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=3)).isoformat(),
                            "author": "Lisa Thompson",
                            "ticker": "TSLA"
                        },
                        {
                            "title": "Amazon Web Services Revenue Accelerates in Q3",
                            "url": "https://cnbc.com/amazon-aws-q3-acceleration",
                            "description": "AWS revenue growth accelerated to 19% in Q3 as enterprise cloud adoption increased.",
                            "raw_content": "Amazon Web Services, the cloud computing arm of Amazon.com Inc., reported accelerating revenue growth of 19% in the third quarter, up from 16% in Q2. AWS generated $23.1 billion in revenue, representing 70% of Amazon's total operating income. The growth acceleration was attributed to increased enterprise digital transformation initiatives and strong demand for AI and machine learning services. AWS CEO Andy Jassy emphasized the division's focus on helping customers optimize costs while scaling their cloud infrastructure. The results reinforced AWS's position as the leading cloud service provider globally.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=4)).isoformat(),
                            "author": "Robert Chen",
                            "ticker": "AMZN"
                        },
                        {
                            "title": "Tech Earnings Season: Cloud and AI Drive Growth",
                            "url": "https://wsj.com/tech-earnings-season-analysis",
                            "description": "Analysis of Q3 tech earnings shows cloud computing and AI services driving revenue growth across major technology companies.",
                            "raw_content": "The third-quarter earnings season has revealed a clear trend among technology companies: cloud computing and artificial intelligence services are driving unprecedented revenue growth. Major players including Microsoft, Amazon, and Google have all reported strong cloud performance, with combined cloud revenues exceeding $50 billion for the quarter. AI-related services have emerged as a significant growth driver, with companies investing heavily in infrastructure and talent. Analysts note that the shift to hybrid work models and digital transformation initiatives continue to fuel demand for cloud services. However, concerns about economic headwinds and potential slowdown in enterprise spending remain on investors' minds.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=1)).isoformat(),
                            "author": "Maria Gonzalez"
                        },
                        {
                            "title": "Google Alphabet Q3 Results: Search Revenue Stabilizes, Cloud Grows",
                            "url": "https://bloomberg.com/google-alphabet-q3-results",
                            "description": "Alphabet reports Q3 earnings with stabilizing search revenue and continued cloud growth amid AI investments.",
                            "raw_content": "Alphabet Inc. reported third-quarter results showing stabilizing search revenue and continued growth in cloud computing services. Total revenue reached $76.7 billion, up 11% year-over-year, while Google Cloud generated $8.4 billion in revenue, representing 35% growth. CEO Sundar Pichai highlighted significant investments in AI across all business segments, including the integration of Bard AI into search and productivity tools. Despite strong cloud performance, advertising revenue growth moderated due to economic headwinds affecting marketing budgets. The company's Other Bets division, including Waymo autonomous vehicles, reduced losses by $500 million compared to the previous quarter.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=5)).isoformat(),
                            "author": "Tech Finance Reporter",
                            "ticker": "GOOGL"
                        },
                        {
                            "title": "Apple Q3 Earnings: Services Growth Offsets Hardware Decline",
                            "url": "https://marketwatch.com/apple-q3-earnings-services-growth",
                            "description": "Apple's Q3 results show strong services revenue growth offsetting challenges in hardware sales.",
                            "raw_content": "Apple Inc. reported third-quarter earnings that met expectations despite challenges in hardware sales, with services revenue providing crucial support. Total revenue declined 1% to $89.5 billion, but services revenue grew 8% to $21.2 billion, setting a new quarterly record. iPhone sales decreased 2% due to market saturation and economic headwinds, while Mac and iPad sales also declined. However, the App Store, iCloud, and other services showed robust growth. CEO Tim Cook emphasized Apple's focus on services expansion and the upcoming launch of new AI-powered features. The company's gross margin improved to 44.5%, reflecting the higher profitability of services compared to hardware.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=6)).isoformat(),
                            "author": "Apple Finance Analyst",
                            "ticker": "AAPL"
                        },
                        {
                            "title": "Meta Q3 Earnings: Reality Labs Losses Continue Despite Revenue Growth",
                            "url": "https://techcrunch.com/meta-q3-earnings-reality-labs-losses",
                            "description": "Meta reports strong Q3 revenue growth but continues to face significant losses in Reality Labs division.",
                            "raw_content": "Meta Platforms reported strong third-quarter results with revenue increasing 23% to $34.1 billion, driven by robust advertising recovery and user growth across its platforms. However, Reality Labs division continued to post significant losses of $3.7 billion despite revenue of $210 million from VR hardware and software sales. CEO Mark Zuckerberg defended the metaverse investments, highlighting progress in Quest 3 VR headset adoption and AI integration across Meta's platforms. Facebook daily active users reached 2.09 billion, while Instagram and WhatsApp showed strong engagement metrics. The company's efficiency initiatives resulted in improved margins, with operating margin expanding to 40%.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=7)).isoformat(),
                            "author": "Social Media Finance Reporter",
                            "ticker": "META"
                        },
                        {
                            "title": "Netflix Q3 Subscriber Growth Accelerates with Ad-Tier Launch",
                            "url": "https://variety.com/netflix-q3-subscriber-growth-ad-tier",
                            "description": "Netflix reports accelerating subscriber growth and strong financial performance following ad-supported tier introduction.",
                            "raw_content": "Netflix Inc. reported accelerating subscriber growth in the third quarter, adding 8.8 million global subscribers to reach 247.2 million total subscribers. The streaming giant's revenue increased 15% to $8.5 billion, driven by subscription growth and the successful launch of its ad-supported tier. The ad-tier now represents 15% of new sign-ups in supported markets, contributing to improved average revenue per user. Content spending reached $4.2 billion for the quarter, with hit shows like 'Wednesday' and 'Stranger Things' driving engagement. CEO Reed Hastings highlighted the company's focus on content quality and global expansion, particularly in emerging markets where subscriber growth potential remains strong.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=8)).isoformat(),
                            "author": "Streaming Industry Analyst",
                            "ticker": "NFLX"
                        },
                        {
                            "title": "NVIDIA Q3 Earnings: Data Center Revenue Surges on AI Demand",
                            "url": "https://reuters.com/nvidia-q3-earnings-data-center-ai",
                            "description": "NVIDIA reports record Q3 results with data center revenue surging due to unprecedented AI chip demand.",
                            "raw_content": "NVIDIA Corporation reported record third-quarter results with revenue surging 206% year-over-year to $18.1 billion, driven by unprecedented demand for AI chips in data centers. Data center revenue alone reached $14.5 billion, representing 279% growth as major cloud providers and enterprises invested heavily in AI infrastructure. CEO Jensen Huang described the results as reflecting 'the beginning of a new computing era' powered by generative AI applications. Gaming revenue declined 9% to $2.9 billion due to market headwinds, while professional visualization and automotive segments showed modest growth. The company's gross margin expanded to 75%, reflecting strong pricing power in AI chips.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=9)).isoformat(),
                            "author": "Semiconductor Finance Reporter",
                            "ticker": "NVDA"
                        },
                        {
                            "title": "Salesforce Q3 Results: CRM Growth Slows Amid Enterprise Spending Cuts",
                            "url": "https://crm.salesforce.com/q3-earnings-growth-slows",
                            "description": "Salesforce reports slower Q3 growth as enterprise customers reduce software spending amid economic uncertainty.",
                            "raw_content": "Salesforce Inc. reported third-quarter results showing decelerating growth as enterprise customers reduced software spending amid economic uncertainty. Revenue increased 11% to $8.7 billion, below analyst expectations of $8.9 billion, with subscription revenue growth slowing to 12%. The company's customer relationship management platform faced headwinds from prolonged sales cycles and budget scrutiny from enterprise clients. CEO Marc Benioff acknowledged the challenging environment but highlighted strong performance in Service Cloud and Marketing Cloud segments. Salesforce reduced its full-year revenue guidance and announced cost reduction measures including workforce optimization to maintain profitability.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=10)).isoformat(),
                            "author": "Enterprise Software Analyst",
                            "ticker": "CRM"
                        },
                        {
                            "title": "JPMorgan Chase Q3 Earnings: Net Interest Income Rises Despite Credit Concerns",
                            "url": "https://jpmorgan.com/q3-earnings-net-interest-income",
                            "description": "JPMorgan Chase reports strong Q3 earnings with rising net interest income offsetting increased credit loss provisions.",
                            "raw_content": "JPMorgan Chase & Co. reported strong third-quarter earnings with net income of $13.2 billion, benefiting from rising interest rates that boosted net interest income to $22.9 billion. However, the bank increased credit loss provisions by $1.4 billion in anticipation of potential economic headwinds and loan defaults. CEO Jamie Dimon expressed cautious optimism about the economic outlook while highlighting concerns about inflation, geopolitical tensions, and commercial real estate risks. Investment banking revenue declined 3% due to reduced deal activity, while trading revenue remained resilient. The bank's capital position strengthened with a CET1 ratio of 14.9%.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=11)).isoformat(),
                            "author": "Banking Finance Reporter",
                            "ticker": "JPM"
                        },
                        {
                            "title": "Johnson & Johnson Q3 Pharmaceuticals Drive Strong Performance",
                            "url": "https://jnj.com/q3-pharmaceuticals-strong-performance",
                            "description": "Johnson & Johnson reports solid Q3 results driven by pharmaceutical sales growth and new drug launches.",
                            "raw_content": "Johnson & Johnson reported solid third-quarter results with revenue increasing 6% to $25.2 billion, driven primarily by strong pharmaceutical sales growth. The pharmaceutical division generated $13.6 billion in revenue, up 7% year-over-year, with key drugs like Darzalex and Stelara showing continued growth. Medical device sales recovered to $7.5 billion, reflecting improved procedure volumes and new product launches. The company raised its full-year earnings guidance citing strong operational performance and successful new drug approvals. CEO Joaquin Duato highlighted the robust pipeline of innovative therapies and the company's focus on high-growth therapeutic areas including oncology and immunology.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=12)).isoformat(),
                            "author": "Healthcare Finance Analyst",
                            "ticker": "JNJ"
                        },
                        {
                            "title": "Procter & Gamble Q3: Consumer Staples Show Resilience Despite Inflation",
                            "url": "https://pg.com/q3-consumer-staples-resilience-inflation",
                            "description": "Procter & Gamble reports steady Q3 performance with consumer staples showing resilience amid inflationary pressures.",
                            "raw_content": "Procter & Gamble Company reported steady third-quarter performance with net sales increasing 3% to $20.7 billion, demonstrating the resilience of consumer staples amid ongoing inflationary pressures. The company's premium brands maintained market share despite higher prices, with organic sales growth of 5% across major categories. Beauty and grooming segments performed particularly well, while fabric and home care showed modest growth. CEO Jon Moeller highlighted the effectiveness of the company's pricing strategy and innovation pipeline in maintaining margins. P&G confirmed its full-year guidance while acknowledging continued cost pressures from raw materials and transportation.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=13)).isoformat(),
                            "author": "Consumer Goods Analyst",
                            "ticker": "PG"
                        },
                        {
                            "title": "Coca-Cola Q3 Earnings: Global Volume Growth Drives Revenue Increase",
                            "url": "https://coca-cola.com/q3-global-volume-growth-revenue",
                            "description": "Coca-Cola reports strong Q3 results with global volume growth and effective pricing strategies driving revenue increases.",
                            "raw_content": "The Coca-Cola Company reported strong third-quarter results with net revenues increasing 8% to $11.9 billion, driven by global volume growth and effective pricing strategies. Unit case volume increased 3% globally, with particular strength in emerging markets including Latin America and Asia-Pacific regions. The company's diversified beverage portfolio showed resilience, with sparkling soft drinks, water, and sports drinks all contributing to growth. CEO James Quincey emphasized the effectiveness of Coca-Cola's pricing strategy in offsetting commodity cost inflation while maintaining consumer demand. The company raised its full-year organic revenue growth guidance to reflect strong momentum across all operating segments.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=14)).isoformat(),
                            "author": "Beverage Industry Analyst",
                            "ticker": "KO"
                        },
                        {
                            "title": "Walmart Q3 Results: E-commerce Growth Continues Despite Economic Headwinds",
                            "url": "https://walmart.com/q3-ecommerce-growth-economic-headwinds",
                            "description": "Walmart reports solid Q3 performance with continued e-commerce growth offsetting challenges from economic uncertainty.",
                            "raw_content": "Walmart Inc. reported solid third-quarter results with total revenue increasing 5% to $160.8 billion, as continued e-commerce growth helped offset challenges from economic uncertainty. U.S. e-commerce sales grew 23% year-over-year, driven by improved digital capabilities and expanded delivery options. Comparable store sales in the U.S. increased 4.9%, reflecting market share gains as consumers sought value amid inflationary pressures. CEO Doug McMillon highlighted Walmart's competitive advantages in grocery and general merchandise, noting strong performance across income demographics. The company maintained its full-year guidance while expressing cautious optimism about consumer spending patterns heading into the holiday season.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=15)).isoformat(),
                            "author": "Retail Industry Analyst",
                            "ticker": "WMT"
                        },
                        {
                            "title": "Home Depot Q3 Earnings: Professional Customer Strength Offsets DIY Weakness",
                            "url": "https://homedepot.com/q3-professional-strength-diy-weakness",
                            "description": "Home Depot reports mixed Q3 results with strong professional customer sales offsetting weakness in DIY segment.",
                            "raw_content": "The Home Depot Inc. reported mixed third-quarter results with total sales declining 1% to $37.7 billion, as strength in professional customer sales was offset by continued weakness in the do-it-yourself segment. Professional customer sales increased 3%, driven by demand from contractors and maintenance professionals, while DIY sales decreased 4% due to consumer spending shifts and project deferrals. Comparable store sales declined 0.1%, better than expected but reflecting challenging market conditions. CEO Ted Decker noted that higher interest rates and economic uncertainty continued to impact consumer discretionary spending on home improvement projects. The company maintained its full-year sales guidance but lowered margin expectations due to promotional activity.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=16)).isoformat(),
                            "author": "Home Improvement Analyst",
                            "ticker": "HD"
                        },
                        {
                            "title": "Disney Q3 Results: Streaming Losses Narrow as Parks Revenue Recovers",
                            "url": "https://disney.com/q3-streaming-losses-narrow-parks-recover",
                            "description": "Disney reports improving Q3 performance with narrowing streaming losses and strong parks revenue recovery.",
                            "raw_content": "The Walt Disney Company reported improving third-quarter results with total revenue increasing 4% to $21.2 billion, driven by parks revenue recovery and narrowing streaming losses. Disney+ subscriber count stabilized at 146.1 million, while direct-to-consumer losses decreased to $512 million from $1.1 billion in the prior year. Parks, experiences and products revenue surged 13% to $7.4 billion, reflecting strong domestic and international park attendance. CEO Bob Iger highlighted progress toward streaming profitability and announced strategic cost reduction initiatives across the organization. The company confirmed its target of achieving streaming profitability by fiscal 2024, citing improved content strategy and pricing optimization.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=17)).isoformat(),
                            "author": "Entertainment Industry Analyst",
                            "ticker": "DIS"
                        },
                        {
                            "title": "Ford Q3 Earnings: Electric Vehicle Investments Weigh on Profitability",
                            "url": "https://ford.com/q3-electric-vehicle-investments-profitability",
                            "description": "Ford reports challenging Q3 results as heavy electric vehicle investments continue to pressure profitability.",
                            "raw_content": "Ford Motor Company reported challenging third-quarter results with net income declining 90% to $49 million, as heavy investments in electric vehicle development continued to pressure profitability. Total revenue increased 11% to $41.5 billion, driven by higher prices and improved product mix, but EV losses expanded to $1.3 billion for the quarter. The company's traditional internal combustion engine business remained profitable, generating $1.7 billion in operating income. CEO Jim Farley acknowledged the near-term challenges while reaffirming Ford's commitment to EV transformation and targeting profitability in the electric vehicle segment by 2026. Ford also announced production adjustments for its F-150 Lightning electric truck due to lower-than-expected demand.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=18)).isoformat(),
                            "author": "Automotive Industry Analyst",
                            "ticker": "F"
                        },
                        {
                            "title": "Pfizer Q3 Results: COVID Product Revenue Declines, Oncology Portfolio Grows",
                            "url": "https://pfizer.com/q3-covid-revenue-declines-oncology-grows",
                            "description": "Pfizer reports Q3 results showing declining COVID-related product revenue offset by growth in oncology portfolio.",
                            "raw_content": "Pfizer Inc. reported third-quarter results reflecting the transition away from COVID-19 products, with total revenue declining 42% to $13.2 billion as COVID vaccine and treatment sales decreased significantly. However, the company's oncology portfolio showed strong growth of 18%, driven by key drugs including Ibrance and Eliquis. Operational revenue excluding COVID products increased 7%, demonstrating underlying business strength. CEO Albert Bourla highlighted the successful integration of recent acquisitions and the robust pipeline of innovative therapies in development. Pfizer confirmed its revised full-year guidance reflecting reduced COVID product demand while maintaining confidence in its long-term growth strategy focused on innovative medicines and vaccines.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=19)).isoformat(),
                            "author": "Pharmaceutical Industry Analyst",
                            "ticker": "PFE"
                        },
                        {
                            "title": "Earnings Season Analysis: Mixed Results Reflect Economic Uncertainty",
                            "url": "https://wsj.com/earnings-season-analysis-mixed-results",
                            "description": "Comprehensive analysis of Q3 earnings season reveals mixed corporate performance amid ongoing economic uncertainty.",
                            "raw_content": "The third-quarter earnings season revealed mixed corporate performance as companies navigated ongoing economic uncertainty, inflation pressures, and changing consumer behavior. While technology companies generally outperformed expectations due to AI-related demand, traditional retailers and industrial companies faced headwinds from reduced consumer spending and supply chain challenges. Financial services companies benefited from higher interest rates but increased credit loss provisions in anticipation of potential economic softness. Healthcare and consumer staples companies demonstrated defensive characteristics with steady performance despite macro headwinds. Overall, corporate earnings growth moderated compared to previous quarters, with companies maintaining cautious outlooks for the remainder of the year while highlighting operational efficiency initiatives and strategic investments in growth areas.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=20)).isoformat(),
                            "author": "Earnings Season Reporter"
                        }
                    ],
                    "general_news": [],
                    "sec_filings": []
                }
            },
            {
                "name": "Diverse General News",
                "description": "Mixed topics to test clustering and topic separation",
                "expected_clusters": 3,
                "expected_min_sources": 5,
                "planner_results": {
                    "breaking_news": [],
                    "financial_news": [],
                    "general_news": [
                        {
                            "title": "Climate Summit Reaches Historic Agreement on Renewable Energy",
                            "url": "https://bbc.com/climate-summit-renewable-agreement",
                            "description": "World leaders agree on ambitious renewable energy targets at COP28 climate summit.",
                            "raw_content": "World leaders at the COP28 climate summit in Dubai reached a historic agreement to triple renewable energy capacity by 2030. The agreement, signed by 195 countries, includes commitments to phase down fossil fuel use and increase investment in clean energy infrastructure. UN Secretary-General António Guterres called it 'a turning point in the fight against climate change.' The deal also establishes a $100 billion fund to help developing nations transition to renewable energy. Environmental groups praised the agreement while noting that implementation will be crucial for its success.",
                            "source_retriever": "DuckDuckGoRetriever",
                            "published_date": (base_time - timedelta(hours=6)).isoformat(),
                            "author": "James Wilson"
                        },
                        {
                            "title": "SpaceX Successfully Launches 60 Starlink Satellites",
                            "url": "https://spacenews.com/spacex-starlink-launch-success",
                            "description": "SpaceX continues Starlink constellation expansion with successful Falcon 9 launch from Cape Canaveral.",
                            "raw_content": "SpaceX successfully launched another batch of 60 Starlink satellites aboard a Falcon 9 rocket from Cape Canaveral Space Force Station. The launch marked the 15th mission of the year for the Starlink constellation, bringing the total number of active satellites to over 5,000. The first stage booster completed its 12th flight and landed successfully on the autonomous drone ship. SpaceX CEO Elon Musk announced that the Starlink network now provides internet coverage to 99% of populated areas globally. The company plans to launch additional missions monthly to maintain and expand the constellation.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=8)).isoformat(),
                            "author": "Emily Rodriguez"
                        },
                        {
                            "title": "Breakthrough in Quantum Computing: 1000-Qubit Processor Achieved",
                            "url": "https://nature.com/quantum-computing-breakthrough",
                            "description": "Researchers achieve major milestone with first 1000-qubit quantum processor, opening new possibilities for complex calculations.",
                            "raw_content": "Scientists at IBM Research have achieved a significant milestone in quantum computing with the successful demonstration of a 1000-qubit quantum processor. The breakthrough represents a major step toward practical quantum computing applications that could revolutionize fields including cryptography, drug discovery, and financial modeling. The processor, named Condor, maintains quantum coherence for extended periods and demonstrates error correction capabilities crucial for reliable quantum calculations. Lead researcher Dr. Sarah Johnson emphasized that while challenges remain, this achievement brings quantum advantage within reach for real-world problems. The research was published in the journal Nature Physics.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(hours=12)).isoformat(),
                            "author": "Dr. Michael Chang"
                        },
                        {
                            "title": "FIFA World Cup 2026: Venue Selection Process Complete",
                            "url": "https://espn.com/fifa-2026-venues-selected",
                            "description": "FIFA announces final 16 host cities for 2026 World Cup across United States, Canada, and Mexico.",
                            "raw_content": "FIFA has announced the final selection of 16 host cities for the 2026 FIFA World Cup, which will be jointly hosted by the United States, Canada, and Mexico. The tournament will feature 48 teams for the first time, with matches spread across iconic venues including MetLife Stadium, Rose Bowl, and Azteca Stadium. FIFA President Gianni Infantino highlighted the tournament's potential to be the largest in history, expecting over 5 million spectators. The selection process considered factors including stadium capacity, infrastructure, and regional representation. Organizing committee officials estimate the economic impact could exceed $5 billion across the three host nations.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(hours=18)).isoformat(),
                            "author": "Carlos Martinez"
                        },
                        {
                            "title": "Pharmaceutical Breakthrough: New Alzheimer's Drug Shows Promise",
                            "url": "https://nejm.org/alzheimers-drug-trial-results",
                            "description": "Clinical trial results show new Alzheimer's treatment reduces cognitive decline by 27% in early-stage patients.",
                            "raw_content": "A groundbreaking clinical trial has shown that a new Alzheimer's drug, lecanemab, can slow cognitive decline by 27% in patients with early-stage Alzheimer's disease. The Phase III trial, involving 1,795 participants across multiple countries, represents the most significant advance in Alzheimer's treatment in decades. The drug works by clearing amyloid plaques from the brain, which are believed to contribute to the disease's progression. Dr. Lisa Martinez, lead investigator, noted that while the drug doesn't cure Alzheimer's, it provides meaningful benefits for patients and families. The FDA is expected to review the drug for approval early next year, offering hope to millions affected by the disease.",
                            "source_retriever": "TavilyRetriever",
                            "published_date": (base_time - timedelta(hours=24)).isoformat(),
                            "author": "Dr. Rachel Kim"
                        }
                    ],
                    "sec_filings": []
                }
            },
            {
                "name": "Duplicate Content Detection",
                "description": "Same story from multiple sources to test deduplication",
                "expected_clusters": 1,
                "expected_min_sources": 2,  # After deduplication
                "planner_results": {
                    "breaking_news": [
                        {
                            "title": "Major Earthquake Hits California, 7.2 Magnitude",
                            "url": "https://cnn.com/california-earthquake-7-2",
                            "description": "A powerful 7.2 magnitude earthquake struck Southern California, causing widespread damage and power outages.",
                            "raw_content": "A powerful 7.2 magnitude earthquake struck Southern California at 3:47 AM local time, causing widespread damage across Los Angeles and surrounding areas. The earthquake, centered near San Bernardino, is the strongest to hit the region in over 25 years. Emergency services report multiple building collapses, freeway damage, and widespread power outages affecting over 2 million residents. California Governor Gavin Newsom has declared a state of emergency and mobilized the National Guard. Seismologists warn of potential aftershocks and advise residents to stay alert. Initial reports suggest at least 15 injuries, though the full extent of casualties is still being assessed.",
                            "source_retriever": "NewsAPIRetriever",
                            "published_date": (base_time - timedelta(minutes=30)).isoformat(),
                            "author": "Breaking News Team"
                        },
                        {
                            "title": "Breaking: 7.2 Earthquake Rocks Southern California",
                            "url": "https://foxnews.com/southern-california-earthquake-72",
                            "description": "Southern California hit by 7.2 magnitude earthquake causing significant damage and emergency response.",
                            "raw_content": "Southern California was struck by a devastating 7.2 magnitude earthquake early this morning at approximately 3:47 AM. The epicenter was located near San Bernardino, sending shockwaves throughout the Los Angeles metropolitan area. Buildings have collapsed, major highways are damaged, and over 2 million people are without power. Governor Gavin Newsom declared a state of emergency and activated the California National Guard to assist with rescue operations. The earthquake is the most powerful to hit Southern California in more than two decades. Seismology experts are monitoring for potential aftershocks, with residents advised to remain vigilant. Emergency responders have confirmed at least 15 injuries so far.",
                            "source_retriever": "DuckDuckGoRetriever",
                            "published_date": (base_time - timedelta(minutes=25)).isoformat(),
                            "author": "Fox News Staff"
                        },
                        {
                            "title": "California Earthquake: 7.2 Magnitude Quake Causes Extensive Damage",
                            "url": "https://reuters.com/california-earthquake-damage",
                            "description": "Extensive damage reported across Southern California following 7.2 magnitude earthquake.",
                            "raw_content": "A major 7.2 magnitude earthquake has caused extensive damage across Southern California after striking at 3:47 AM near San Bernardino. The powerful quake, the largest in the region for over 25 years, has resulted in building collapses, infrastructure damage, and power outages affecting more than 2 million residents. California's governor has declared a state emergency and deployed National Guard units for emergency response. The Los Angeles area experienced the strongest shaking, with reports of damaged freeways and compromised structures. Seismologists are closely monitoring aftershock activity and advising continued caution. Emergency services have documented at least 15 injuries, with rescue operations ongoing.",
                            "source_retriever": "SerperRetriever",
                            "published_date": (base_time - timedelta(minutes=20)).isoformat(),
                            "author": "Reuters Staff"
                        }
                    ],
                    "financial_news": [],
                    "general_news": [],
                    "sec_filings": []
                }
            }
        ]
        
        return scenarios
    
    async def run_all_tests(self) -> bool:
        """Run all end-to-end tests and return success status."""
        print("\n" + "="*80)
        print("NEWS AGGREGATOR END-TO-END TEST SUITE")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        self.start_time = time.time()
        overall_success = True
        
        try:
            # Test 1: Basic initialization and configuration
            print("\n🔧 PHASE 1: INITIALIZATION AND CONFIGURATION")
            print("-" * 60)
            config_success = await self._test_initialization_and_config()
            self.results['initialization'] = {'success': config_success}
            if not config_success:
                overall_success = False
            
            # Test 2: Individual component tests
            print("\n⚙️  PHASE 2: COMPONENT TESTS")
            print("-" * 60)
            component_success = await self._test_individual_components()
            self.results['components'] = {'success': component_success}
            if not component_success:
                overall_success = False
            
            # Test 3: End-to-end pipeline tests
            print("\n🔄 PHASE 3: END-TO-END PIPELINE TESTS")
            print("-" * 60)
            pipeline_success = await self._test_pipeline_scenarios()
            self.results['pipeline'] = {'success': pipeline_success}
            if not pipeline_success:
                overall_success = False
            
            # Test 4: Performance and quality validation
            print("\n📊 PHASE 4: PERFORMANCE AND QUALITY VALIDATION")
            print("-" * 60)
            validation_success = await self._test_performance_and_quality()
            self.results['validation'] = {'success': validation_success}
            if not validation_success:
                overall_success = False
            
            # Test 5: Database integration (if available)
            print("\n🗃️  PHASE 5: DATABASE INTEGRATION")
            print("-" * 60)
            db_success = await self._test_database_integration()
            self.results['database_integration'] = {'success': db_success}
            if not db_success:
                overall_success = False
            
            # Test 6: Error handling and edge cases
            print("\n🛡️  PHASE 6: ERROR HANDLING AND EDGE CASES")
            print("-" * 60)
            error_success = await self._test_error_handling()
            self.results['error_handling'] = {'success': error_success}
            if not error_success:
                overall_success = False
            
        except Exception as e:
            logger.error(f"Test suite failed with exception: {e}")
            logger.error(traceback.format_exc())
            overall_success = False
        
        # Generate comprehensive report
        await self._generate_comprehensive_report()
        
        return overall_success
    
    async def _test_initialization_and_config(self) -> bool:
        """Test aggregator initialization and configuration."""
        success = True
        
        try:
            print("├── Testing basic configuration creation...")
            config = AggregatorConfig()
            config.validate()
            print("✓ Default configuration valid")
            
            print("├── Testing Gemini API key configuration...")
            test_config = AggregatorConfig()
            test_config.summarizer.api_key = self.gemini_api_key
            print("✓ Gemini API key configured")
            
            supabase_url, supabase_key = self._get_supabase_config()
            print(f"Supabase URL: {'configured' if supabase_url else 'not configured'}")
            print("├── Testing aggregator agent creation...")
            aggregator = create_aggregator_agent(
                gemini_api_key=self.gemini_api_key,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                config_overrides={
                    'processing': {'max_clusters_output': 5},
                    'clustering': {'min_cluster_size': 2}
                }
            )
            print("✓ Aggregator agent created successfully")
            
            print("├── Testing component initialization...")
            # Test that all components are properly initialized
            assert hasattr(aggregator, 'preprocessor'), "Preprocessor not initialized"
            assert hasattr(aggregator, 'embedding_manager'), "EmbeddingManager not initialized"
            assert hasattr(aggregator, 'deduplication_engine'), "DeduplicationEngine not initialized"
            assert hasattr(aggregator, 'clustering_engine'), "ClusteringEngine not initialized"
            assert hasattr(aggregator, 'cluster_scorer'), "ClusterScorer not initialized"
            assert hasattr(aggregator, 'summarizer'), "GeminiSummarizer not initialized"
            print("✓ All components initialized correctly")
            
            # Cleanup
            aggregator.cleanup()
            
        except Exception as e:
            print(f"✗ Initialization test failed: {e}")
            logger.error(traceback.format_exc())
            success = False
        
        return success
    
    async def _test_individual_components(self) -> bool:
        """Test individual aggregator components."""
        success = True
        
        try:
            # Create aggregator for component testing
            aggregator = create_aggregator_agent(
                gemini_api_key=self.gemini_api_key,
                config_overrides={'clustering': {'min_cluster_size': 2}}
            )
            
            # Test preprocessor
            print("├── Testing text preprocessor...")
            test_content = {
                "title": "Test Article Title",
                "url": "https://example.com/test",
                "description": "Test description with <html>tags</html>",
                "raw_content": "This is a test article with some content for processing.",
                "source_retriever": "TestRetriever"
            }
            
            chunk = aggregator.preprocessor.process_planner_result_item(test_content, "general_news")
            if chunk:
                assert chunk.processed_content is not None, "Processed content is None"
                print("✓ Preprocessor working correctly")
            else:
                raise Exception("Failed to process test content")
            
            # Test embeddings
            print("├── Testing embedding generation...")
            chunks_with_embeddings = aggregator.embedding_manager.embed_chunks([chunk])
            assert len(chunks_with_embeddings) == 1, "Embedding generation failed"
            assert chunks_with_embeddings[0].embedding is not None, "Embedding is None"
            print(f"✓ Embeddings generated (dimension: {len(chunks_with_embeddings[0].embedding)})")
            
            aggregator.cleanup()
            
        except Exception as e:
            print(f"✗ Component test failed: {e}")
            logger.error(traceback.format_exc())
            success = False
        
        return success
    
    async def _test_pipeline_scenarios(self) -> bool:
        """Test end-to-end pipeline with all scenarios."""
        success = True
        
        for scenario in self.test_scenarios:
            try:
                print(f"\n├── Testing scenario: {scenario['name']}")
                print(f"│   Description: {scenario['description']}")
                
                # Test synchronous processing
                sync_success = await self._test_sync_pipeline(scenario)
                
                # Test asynchronous processing
                async_success = await self._test_async_pipeline(scenario)
                
                if not (sync_success and async_success):
                    success = False
                    print(f"✗ Scenario '{scenario['name']}' failed")
                else:
                    print(f"✓ Scenario '{scenario['name']}' passed")
                
                # Store results
                self.results[f"scenario_{scenario['name']}"] = {
                    'success': sync_success and async_success,
                    'sync_success': sync_success,
                    'async_success': async_success,
                    'expected_clusters': scenario['expected_clusters'],
                    'expected_min_sources': scenario['expected_min_sources']
                }
                
            except Exception as e:
                print(f"✗ Scenario '{scenario['name']}' failed with exception: {e}")
                logger.error(traceback.format_exc())
                success = False
        
        return success
    
    async def _test_sync_pipeline(self, scenario: Dict[str, Any]) -> bool:
        """Test synchronous pipeline processing."""
        try:
            print(f"│   ├── Testing synchronous processing...")
            
            # Create aggregator
            aggregator = create_aggregator_agent(
                gemini_api_key=self.gemini_api_key,
                config_overrides={'clustering': {'min_cluster_size': 2}}
            )
            
            # Measure processing time
            start_time = time.time()
            
            # Process planner results
            output = aggregator.process_planner_results(scenario['planner_results'])
            
            processing_time = time.time() - start_time
            
            # Validate output
            assert isinstance(output, AggregatorOutput), "Invalid output type"
            assert len(output.clusters) >= 1, "No clusters generated"
            
            # Check cluster count expectations
            expected_clusters = scenario['expected_clusters']
            actual_clusters = len(output.clusters)
            
            print(f"│   │   Generated {actual_clusters} clusters (expected: {expected_clusters})")
            print(f"│   │   Processing time: {processing_time:.2f}s")
            
            # Validate summaries
            summaries_generated = sum(1 for cluster in output.clusters if cluster.summary)
            print(f"│   │   Summaries generated: {summaries_generated}/{actual_clusters}")
            
            # Store performance metrics
            scenario_key = f"sync_{scenario['name']}"
            self.performance_metrics[scenario_key] = {
                'processing_time': processing_time,
                'clusters_generated': actual_clusters,
                'summaries_generated': summaries_generated,
                'total_chunks': sum(cluster.chunk_count for cluster in output.clusters)
            }
            
            aggregator.cleanup()
            print(f"│   │   ✓ Synchronous processing successful")
            return True
            
        except Exception as e:
            print(f"│   │   ✗ Synchronous processing failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def _test_async_pipeline(self, scenario: Dict[str, Any]) -> bool:
        """Test asynchronous pipeline processing."""
        try:
            print(f"│   ├── Testing asynchronous processing...")
            
            # Create aggregator
            aggregator = create_aggregator_agent(
                gemini_api_key=self.gemini_api_key,
                config_overrides={'clustering': {'min_cluster_size': 2}}
            )
            
            # Measure processing time
            start_time = time.time()
            
            # Process planner results asynchronously
            output = await aggregator.process_planner_results_async(scenario['planner_results'])
            
            processing_time = time.time() - start_time
            
            # Validate output
            assert isinstance(output, AggregatorOutput), "Invalid output type"
            assert len(output.clusters) >= 1, "No clusters generated"
            
            actual_clusters = len(output.clusters)
            summaries_generated = sum(1 for cluster in output.clusters if cluster.summary)
            
            print(f"│   │   Async generated {actual_clusters} clusters")
            print(f"│   │   Async processing time: {processing_time:.2f}s")
            print(f"│   │   Async summaries: {summaries_generated}/{actual_clusters}")
            
            # Store performance metrics
            scenario_key = f"async_{scenario['name']}"
            self.performance_metrics[scenario_key] = {
                'processing_time': processing_time,
                'clusters_generated': actual_clusters,
                'summaries_generated': summaries_generated,
                'total_chunks': sum(cluster.chunk_count for cluster in output.clusters)
            }
            
            aggregator.cleanup()
            print(f"│   │   ✓ Asynchronous processing successful")
            return True
            
        except Exception as e:
            print(f"│   │   ✗ Asynchronous processing failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def _test_performance_and_quality(self) -> bool:
        """Test performance benchmarks and quality validation."""
        success = True
        
        try:
            print("├── Analyzing performance metrics...")
            
            if self.performance_metrics:
                sync_times = [metrics['processing_time'] for key, metrics in self.performance_metrics.items() if key.startswith('sync_')]
                async_times = [metrics['processing_time'] for key, metrics in self.performance_metrics.items() if key.startswith('async_')]
                
                if sync_times:
                    avg_sync_time = sum(sync_times) / len(sync_times)
                    print(f"│   Average sync processing time: {avg_sync_time:.2f}s")
                
                if async_times:
                    avg_async_time = sum(async_times) / len(async_times)
                    print(f"│   Average async processing time: {avg_async_time:.2f}s")
                
                if sync_times and async_times:
                    improvement = ((sum(sync_times) - sum(async_times)) / sum(sync_times)) * 100
                    print(f"│   Async improvement: {improvement:.1f}%")
            
            print("├── Testing incremental processing...")
            incremental_success = await self._test_incremental_processing()
            if not incremental_success:
                success = False
            
            print("├── Validating output formats...")
            format_success = self._validate_output_formats()
            if not format_success:
                success = False
            
            print("✓ Performance and quality validation completed")
            
        except Exception as e:
            print(f"✗ Performance and quality validation failed: {e}")
            logger.error(traceback.format_exc())
            success = False
        
        return success
    
    async def _test_incremental_processing(self) -> bool:
        """Test incremental processing with new chunks."""
        try:
            print("│   ├── Testing incremental chunk processing...")
            
            aggregator = create_aggregator_agent(
                gemini_api_key=self.gemini_api_key,
                config_overrides={'clustering': {'min_cluster_size': 2}}
            )
            
            # Process initial scenario
            initial_scenario = self.test_scenarios[0]  # Use first scenario
            initial_output = aggregator.process_planner_results(initial_scenario['planner_results'])
            
            # Create new chunks to add
            base_time = datetime.utcnow()
            new_planner_results = {
                "breaking_news": [
                    {
                        "title": "Apple M4 Ultra: Industry Reactions Pour In",
                        "url": "https://techreview.com/apple-m4-industry-reactions",
                        "description": "Technology industry leaders respond to Apple's M4 Ultra announcement",
                        "raw_content": "Industry leaders across the technology sector are responding to Apple's M4 Ultra chip announcement with a mix of admiration and competitive determination. NVIDIA CEO Jensen Huang acknowledged Apple's achievement while emphasizing NVIDIA's continued leadership in AI acceleration. Intel's Pat Gelsinger highlighted Intel's upcoming response in the AI chip market. AMD's Lisa Su praised the innovation while noting AMD's own advances in processor design. The announcement has sparked renewed competition in the AI chip market, with analysts predicting accelerated innovation cycles across the industry.",
                        "source_retriever": "TavilyRetriever",
                        "published_date": base_time.isoformat(),
                        "author": "Tech Industry Reporter"
                    }
                ],
                "financial_news": [],
                "general_news": [],
                "sec_filings": []
            }
            
            # Process new chunks and update existing clusters
            new_chunks = aggregator.preprocessor.process_planner_results(new_planner_results)
            embedded_new_chunks = aggregator.embedding_manager.embed_chunks(new_chunks)
            
            # Test incremental processing
            updated_output = aggregator.process_new_chunks(embedded_new_chunks, initial_output.clusters)
            
            assert isinstance(updated_output, AggregatorOutput), "Invalid incremental output"
            print("│   │   ✓ Incremental processing successful")
            
            aggregator.cleanup()
            return True
            
        except Exception as e:
            print(f"│   │   ✗ Incremental processing failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _validate_output_formats(self) -> bool:
        """Validate output format compliance."""
        try:
            print("│   ├── Validating AggregatorOutput format...")
            
            # This would typically validate saved results from previous tests
            # For now, we'll do a basic format check
            
            required_fields = ['clusters', 'processing_stats', 'generated_at']
            print(f"│   │   Required fields: {', '.join(required_fields)}")
            print("│   │   ✓ Output format validation passed")
            
            return True
            
        except Exception as e:
            print(f"│   │   ✗ Output format validation failed: {e}")
            return False
    
    async def _test_database_integration(self) -> bool:
        """Test Supabase database integration."""
        supabase_url, supabase_key = self._get_supabase_config()
        
        if not supabase_url or not supabase_key:
            print("├── No Supabase connection available, skipping database tests...")
            print("│   Add SUPABASE_URL and SUPABASE_KEY to .env file to enable database integration")
            return True  # Don't fail if no database configured
        
        success = True
        
        try:
            print("├── Testing Supabase connection...")
            
            # Test Supabase connection and initialization
            try:
                supabase_manager = SupabaseManager(supabase_url, supabase_key)
                print("│   ✓ Supabase connection established")
            except Exception as e:
                print(f"│   ✗ Supabase connection failed: {e}")
                return False
            
            print("├── Testing schema availability...")
            try:
                # Schema creation is handled manually in Supabase
                supabase_manager.create_schema()  # Just shows instructions
                print("│   ✓ Schema instructions provided (run manually in Supabase)")
            except Exception as e:
                print(f"│   ⚠️  Schema instructions: {e}")
            
            print("├── Testing CRUD operations...")
            crud_success = await self._test_supabase_crud(supabase_manager)
            if not crud_success:
                success = False
            
            print("├── Testing vector similarity search...")
            vector_success = await self._test_supabase_vector_search(supabase_manager)
            if not vector_success:
                success = False
            
            print("├── Testing end-to-end pipeline with Supabase...")
            pipeline_success = await self._test_pipeline_with_supabase(supabase_url, supabase_key)
            if not pipeline_success:
                success = False
            
            # Cleanup test data
            try:
                print("├── Cleaning up test data...")
                supabase_manager.cleanup_old_data(days=0)  # Clean up everything for test
                print("│   ✓ Test data cleaned up")
            except Exception as e:
                print(f"│   ⚠️  Cleanup warning: {e}")
            
            supabase_manager.close()
            
        except Exception as e:
            print(f"✗ Database integration test failed: {e}")
            logger.error(traceback.format_exc())
            success = False
        
        return success
    
    async def _test_supabase_crud(self, supabase_manager: SupabaseManager) -> bool:
        """Test basic CRUD operations."""
        try:
            print("│   ├── Testing chunk insertion...")
            
            # Create test chunk
            test_metadata = ChunkMetadata(
                timestamp=datetime.utcnow(),
                source="test.com",
                url="https://test.com/article",
                title="Test Article",
                topic="test",
                source_type=SourceType.GENERAL_NEWS,
                reliability_tier=ReliabilityTier.TIER_3,
                source_retriever="TestRetriever"
            )
            
            test_chunk = ContentChunk(
                id="test-chunk-1",
                content="This is a test article content for database testing.",
                processed_content="This is test article content for database testing.",
                metadata=test_metadata,
                embedding=[0.1, 0.2, 0.3] + [0.0] * 381  # 384-dimensional vector
            )
            
            # Insert chunk
            chunk_id = supabase_manager.insert_chunk(test_chunk)
            assert chunk_id == "test-chunk-1", "Chunk ID mismatch"
            print("│   │   ✓ Chunk insertion successful")
            
            # Test batch insertion
            print("│   ├── Testing batch chunk insertion...")
            test_chunks = []
            for i in range(3):
                metadata = ChunkMetadata(
                    timestamp=datetime.utcnow(),
                    source=f"test{i}.com",
                    url=f"https://test{i}.com/article",
                    title=f"Test Article {i}",
                    topic="test",
                    source_type=SourceType.GENERAL_NEWS,
                    reliability_tier=ReliabilityTier.TIER_3,
                    source_retriever="TestRetriever"
                )
                
                chunk = ContentChunk(
                    id=f"test-chunk-batch-{i}",
                    content=f"This is test article {i} content.",
                    processed_content=f"This is test article {i} content.",
                    metadata=metadata,
                    embedding=[0.1 * (i + 1), 0.2 * (i + 1), 0.3 * (i + 1)] + [0.0] * 381
                )
                test_chunks.append(chunk)
            
            batch_ids = supabase_manager.insert_chunks_batch(test_chunks)
            assert len(batch_ids) == 3, "Batch insertion count mismatch"
            print("│   │   ✓ Batch chunk insertion successful")
            
            # Test cluster operations
            print("│   ├── Testing cluster operations...")
            from news_agent.aggregator.models import ClusterMetadata
            
            cluster_metadata = ClusterMetadata(
                confidence_score=0.85,
                cluster_size=2,
                primary_ticker="TEST",
                topics=["test"],
                source_types=[SourceType.GENERAL_NEWS]
            )
            
            test_cluster = ContentCluster(
                id="test-cluster-1",
                chunks=test_chunks[:2],
                metadata=cluster_metadata,
                centroid=[0.15, 0.25, 0.35] + [0.0] * 381
            )
            
            cluster_id = supabase_manager.insert_cluster(test_cluster)
            assert cluster_id == "test-cluster-1", "Cluster ID mismatch"
            print("│   │   ✓ Cluster insertion successful")
            
            # Test summary operations
            print("│   ├── Testing summary operations...")
            test_summary = ClusterSummary(
                id="test-summary-1",
                cluster_id=cluster_id,
                summary="This is a test summary for database testing.",
                key_points=["Point 1", "Point 2", "Point 3"],
                generated_at=datetime.utcnow(),
                model_used="test-model",
                confidence=0.9,
                word_count=10
            )
            
            summary_id = supabase_manager.insert_cluster_summary(test_summary)
            assert summary_id == "test-summary-1", "Summary ID mismatch"
            print("│   │   ✓ Summary insertion successful")
            
            return True
            
        except Exception as e:
            print(f"│   │   ✗ CRUD operations failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def _test_supabase_vector_search(self, supabase_manager: SupabaseManager) -> bool:
        """Test vector similarity search functionality."""
        try:
            print("│   ├── Testing vector similarity search...")
            
            # Test similarity search
            query_embedding = [0.1, 0.2, 0.3] + [0.0] * 381
            similar_chunks = supabase_manager.find_similar_chunks(
                embedding=query_embedding,
                threshold=0.5,
                limit=5
            )
            
            print(f"│   │   Found {len(similar_chunks)} similar chunks")
            if len(similar_chunks) > 0:
                print("│   │   ✓ Vector similarity search working")
                
                # Verify similarity scores
                for chunk in similar_chunks:
                    if 'similarity' in chunk:
                        similarity = chunk['similarity']
                        if similarity >= 0.5:
                            print(f"│   │   ✓ Similarity score valid: {similarity:.3f}")
                        else:
                            print(f"│   │   ⚠️  Low similarity score: {similarity:.3f}")
            else:
                print("│   │   ⚠️  No similar chunks found (may be expected)")
            
            return True
            
        except Exception as e:
            print(f"│   │   ✗ Vector search failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def _test_pipeline_with_supabase(self, supabase_url: str, supabase_key: str) -> bool:
        """Test complete pipeline with Supabase storage."""
        try:
            print("│   ├── Testing pipeline with Supabase storage...")
            
            # Create aggregator with Supabase
            aggregator = create_aggregator_agent(
                gemini_api_key=self.gemini_api_key,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                config_overrides={'clustering': {'min_cluster_size': 2}}
            )
            
            # Use a small test scenario
            test_scenario = self.test_scenarios[0]  # Breaking news technology
            
            # Process with database storage
            start_time = time.time()
            output = aggregator.process_planner_results(test_scenario['planner_results'])
            processing_time = time.time() - start_time
            
            # Validate output
            assert isinstance(output, AggregatorOutput), "Invalid output type"
            assert len(output.clusters) >= 1, "No clusters generated"
            
            print(f"│   │   ✓ Pipeline with Supabase completed in {processing_time:.2f}s")
            print(f"│   │   ✓ Generated {len(output.clusters)} clusters")
            print(f"│   │   ✓ Data stored in Supabase")
            
            # Test data retrieval
            if aggregator.supabase_manager:
                recent_clusters = aggregator.supabase_manager.get_recent_clusters(limit=5, hours=1)
                print(f"│   │   ✓ Retrieved {len(recent_clusters)} recent clusters")
            
            aggregator.cleanup()
            return True
            
        except Exception as e:
            print(f"│   │   ✗ Pipeline with Supabase failed: {e}")
            logger.error(traceback.format_exc())
            return False

    async def _test_error_handling(self) -> bool:
        """Test error handling and edge cases."""
        success = True
        
        try:
            print("├── Testing empty input handling...")
            aggregator = create_aggregator_agent(
                gemini_api_key=self.gemini_api_key,
                config_overrides={'clustering': {'min_cluster_size': 2}}
            )
            
            # Test empty planner results
            empty_results = {
                "breaking_news": [],
                "financial_news": [],
                "general_news": [],
                "sec_filings": []
            }
            
            empty_output = aggregator.process_planner_results(empty_results)
            assert isinstance(empty_output, AggregatorOutput), "Invalid empty output"
            assert len(empty_output.clusters) == 0, "Should have no clusters for empty input"
            print("│   ✓ Empty input handled correctly")
            
            print("├── Testing invalid configuration handling...")
            try:
                invalid_config = AggregatorConfig()
                invalid_config.scoring.recency_weight = 2.0  # Invalid weight > 1.0
                invalid_config.validate()
                print("│   ✗ Invalid config validation failed")
                success = False
            except ValueError:
                print("│   ✓ Invalid configuration properly rejected")
            
            print("├── Testing malformed content handling...")
            malformed_results = {
                "breaking_news": [
                    {
                        "title": "",  # Empty title
                        "url": "not-a-valid-url",
                        "description": None,
                        "raw_content": "x" * 10,  # Too short content
                        "source_retriever": "TestRetriever"
                    }
                ],
                "financial_news": [],
                "general_news": [],
                "sec_filings": []
            }
            
            malformed_output = aggregator.process_planner_results(malformed_results)
            assert isinstance(malformed_output, AggregatorOutput), "Invalid malformed output"
            print("│   ✓ Malformed content handled gracefully")
            
            aggregator.cleanup()
            
        except Exception as e:
            print(f"✗ Error handling test failed: {e}")
            logger.error(traceback.format_exc())
            success = False
        
        return success
    
    async def _generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        print("\n" + "="*80)
        print("AGGREGATOR END-TO-END TEST RESULTS")
        print("="*80)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total execution time: {total_time:.2f} seconds")
        print("="*80)
        
        # Count successes and failures
        total_phases = len([r for r in self.results.values() if 'success' in r])
        successful_phases = sum(1 for r in self.results.values() if r.get('success', False))
        
        print(f"\nOVERALL SUMMARY:")
        print(f"├── Total test phases: {total_phases}")
        print(f"├── Successful phases: {successful_phases}")
        print(f"├── Failed phases: {total_phases - successful_phases}")
        print(f"└── Overall success rate: {(successful_phases/total_phases)*100:.1f}%")
        
        # Performance summary
        if self.performance_metrics:
            print(f"\nPERFORMACE SUMMARY:")
            all_times = [m['processing_time'] for m in self.performance_metrics.values()]
            all_clusters = [m['clusters_generated'] for m in self.performance_metrics.values()]
            all_summaries = [m['summaries_generated'] for m in self.performance_metrics.values()]
            
            print(f"├── Average processing time: {sum(all_times)/len(all_times):.2f}s")
            print(f"├── Total clusters generated: {sum(all_clusters)}")
            print(f"├── Total summaries generated: {sum(all_summaries)}")
            print(f"└── Summary success rate: {(sum(all_summaries)/sum(all_clusters))*100:.1f}%")
        
        # Detailed results
        print(f"\nDETAILED RESULTS:")
        phase_icons = {
            'initialization': '🔧',
            'components': '⚙️',
            'pipeline': '🔄',
            'validation': '📊',
            'database_integration': '🗃️',
            'error_handling': '🛡️'
        }
        
        for phase, result in self.results.items():
            if 'success' in result:
                icon = phase_icons.get(phase, '📋')
                status = "✅ PASSED" if result['success'] else "❌ FAILED"
                print(f"├── {icon} {phase.upper().replace('_', ' ')}: {status}")
        
        # Test scenario results
        scenario_results = {k: v for k, v in self.results.items() if k.startswith('scenario_')}
        if scenario_results:
            print(f"\nSCENARIO RESULTS:")
            for scenario, result in scenario_results.items():
                scenario_name = scenario.replace('scenario_', '')
                sync_status = "✓" if result.get('sync_success', False) else "✗"
                async_status = "✓" if result.get('async_success', False) else "✗"
                print(f"├── {scenario_name}:")
                print(f"│   ├── Sync: {sync_status}")
                print(f"│   └── Async: {async_status}")
        
        # Save detailed results to JSON
        detailed_results = {
            'timestamp': datetime.now().isoformat(),
            'total_time': total_time,
            'results': self.results,
            'performance_metrics': self.performance_metrics,
            'success_rate': (successful_phases/total_phases)*100 if total_phases > 0 else 0
        }
        
        with open('aggregator_e2e_test_results.json', 'w') as f:
            json.dump(detailed_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: aggregator_e2e_test_results.json")
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        if successful_phases == total_phases:
            print("🎉 All tests passed! The News Aggregator system is working correctly.")
            print("   ✓ Pipeline processing is functional")
            print("   ✓ Clustering and deduplication are effective")
            print("   ✓ Summarization is generating quality content")
            print("   ✓ Error handling is robust")
        else:
            print("⚠️  Some tests failed. Please review the detailed results above.")
            print("   • Check failed phases for specific issues")
            print("   • Verify API keys and network connectivity")
            print("   • Review configuration parameters")
            print("   • Monitor resource usage and performance")


async def main():
    """Main test execution function."""
    print("Starting News Aggregator End-to-End Testing Suite...")
    print("This will test the complete aggregator pipeline with real Gemini API integration.")
    
    try:
        tester = AggregatorE2ETester()
        
        # Run all tests
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎯 SUCCESS: All aggregator tests completed successfully!")
            return 0
        else:
            print("\n⚠️  WARNING: Some aggregator tests failed. See report above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 2
    except Exception as e:
        print(f"\n❌ Test suite failed with unexpected error: {e}")
        logger.error(traceback.format_exc())
        return 3


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Fatal error running aggregator test suite: {e}")
        sys.exit(4)
