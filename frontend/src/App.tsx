import React, { useState, useEffect } from 'react';
import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';
import { ethers } from 'ethers';
import './index.css';

declare global {
  interface Window {
    ethereum?: any;
  }
}

const CHAIN_ID_HEX = `0x${studionet.id.toString(16)}`;
const RPC_URL = studionet.rpcUrls.default.http[0];
const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS || '';

async function callWithRetry<T>(
  fn: () => Promise<T>, 
  retries = 5, 
  delay = 2500,
  onRetry?: (attempt: number, error: any) => void
): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (err: any) {
      const errMsg = err.message?.toLowerCase() || '';
      const isRateLimit = errMsg.includes('rate limit') || 
                          errMsg.includes('rate-limit') || 
                          errMsg.includes('too many requests') || 
                          errMsg.includes('429');
      const isNetworkError = isRateLimit ||
                            errMsg.includes('failed to fetch') || 
                            errMsg.includes('network error') ||
                            errMsg.includes('rpc error') ||
                            errMsg.includes('request timed out') ||
                            errMsg.includes('forbidden') ||
                            errMsg.includes('403');
      if (isNetworkError && i < retries - 1) {
        const waitTime = isRateLimit ? 3500 : delay;
        console.warn(`[GenLayer RPC] ${isRateLimit ? 'Rate Limited' : 'Network Error'}. Retrying attempt ${i + 2}/${retries} in ${waitTime}ms...`, err);
        if (onRetry) {
          onRetry(i + 2, err);
        }
        await new Promise((resolve) => setTimeout(resolve, waitTime));
        continue;
      }
      throw err;
    }
  }
  throw new Error("RPC request failed after maximum retries");
}

function App() {
  const [account, setAccount] = useState<string | null>(null);
  const [client, setClient] = useState<any>(null);
  
  // Dashboard Role
  const [role, setRole] = useState<'EXPLORE' | 'BRAND' | 'CREATOR' | 'BOUNTIES'>('EXPLORE');

  // Campaign State
  const [campaignId, setCampaignId] = useState<string>('');
  const [campaignData, setCampaignData] = useState<any>(null);
  const [myCampaigns, setMyCampaigns] = useState<any[]>([]);
  
  // Action States
  const [videoUrl, setVideoUrl] = useState('');
  const [appealText, setAppealText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Create Campaign State (Brand)
  const [newCampId, setNewCampId] = useState('');
  const [creatorAddress, setCreatorAddress] = useState('');
  const [escrowAmount, setEscrowAmount] = useState('');
  const [blacklistKeywords, setBlacklistKeywords] = useState('');
  const [productName, setProductName] = useState('');
  const [requiredCta, setRequiredCta] = useState('');
  const [requiredLang, setRequiredLang] = useState('');
  const [campaignDesc, setCampaignDesc] = useState('');
  const [brandLogo, setBrandLogo] = useState('');
  const [logoUrl, setLogoUrl] = useState('');
  const [isCampaignCreated, setIsCampaignCreated] = useState(false);
  const [createdCampaignId, setCreatedCampaignId] = useState('');

  const connectWallet = async () => {
    if (!window.ethereum) {
      alert('MetaMask is required to use this DApp.');
      return;
    }
    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const address = accounts[0];
      
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: CHAIN_ID_HEX }],
        });
      } catch (switchError: any) {
        if (switchError.code === 4902) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [
              {
                chainId: CHAIN_ID_HEX,
                chainName: studionet.name,
                rpcUrls: [RPC_URL], 
                nativeCurrency: studionet.nativeCurrency,
              },
            ],
          });
        }
      }
      setAccount(address);
      const genClient = createClient({
        chain: studionet,
        account: address as `0x${string}`,
        provider: window.ethereum
      });
      setClient(genClient);
      localStorage.setItem('walletConnected', 'true');
    } catch (error) {
      console.error("Connection failed", error);
    }
  };

  const disconnectWallet = () => {
    setAccount(null);
    setClient(null);
    setCampaignData(null);
    localStorage.removeItem('walletConnected');
    setSuccessMsg('Wallet disconnected.');
  };

  // ---------------- BRAND ACTIONS ----------------

  const createCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!client || !CONTRACT_ADDRESS) {
      alert('Please connect wallet and configure contract.');
      return;
    }
    setIsSubmitting(true);
    setLoadingMsg('Creating Campaign and Deposting Funds...');
    setSuccessMsg('');
    try {
      const cleanAmount = escrowAmount.replace(',', '.').trim();
      const amountInWei = ethers.parseEther(cleanAmount);
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'create_campaign',
        args: [newCampId, creatorAddress.trim(), blacklistKeywords, productName.trim(), requiredCta.trim(), requiredLang.trim(), campaignDesc.trim(), brandLogo.trim(), logoUrl.trim()],
        value: amountInWei
      }));
      
      setLoadingMsg('Waiting for campaign creation block finalization...');
      await client.waitForTransactionReceipt({ hash: txHash });
      
      setSuccessMsg(`Campaign ${newCampId} created successfully! Escrow deposited.`);
      setCampaignId(newCampId);
      setIsCampaignCreated(true);
      setCreatedCampaignId(newCampId);
      // Clean form
      setNewCampId('');
      setCreatorAddress('');
      setEscrowAmount('');
      setBlacklistKeywords('');
      setProductName('');
      setRequiredCta('');
      setRequiredLang('');
      setCampaignDesc('');
      setBrandLogo('');
      setLogoUrl('');
      // Auto fetch the newly created campaign
      fetchCampaign(newCampId);
    } catch (error: any) {
      console.error(error);
      const isFetchErr = error.message?.toLowerCase().includes('failed to fetch') || error.message?.toLowerCase().includes('rpc error');
      if (isFetchErr) {
        alert('GenLayer RPC Error: The testnet node is currently busy or rate-limiting requests. Please wait a few seconds and try again.');
      } else {
        alert('Transaction failed: ' + error.message);
      }
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const requestCancelCampaign = async () => {
    if (!client || !CONTRACT_ADDRESS) return;
    setIsSubmitting(true);
    setLoadingMsg('Requesting cancellation...');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'cancel_campaign',
        args: [campaignId]
      }));
      setLoadingMsg('Finalizing cancellation request on GenLayer...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Cancellation requested! Waiting for Creator approval or 7-day timeout.');
    } catch(error: any) {
      console.error(error);
      alert('Cancel failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const forceCancelCampaign = async () => {
    if (!client || !CONTRACT_ADDRESS) return;
    setIsSubmitting(true);
    setLoadingMsg('Force cancelling campaign...');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'force_cancel',
        args: [campaignId]
      }));
      setLoadingMsg('Finalizing force cancellation on GenLayer...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Campaign force cancelled and funds refunded.');
    } catch(error: any) {
      console.error(error);
      alert('Force cancel failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const resolveDispute = async (resolution: string) => {
    if (!client || !CONTRACT_ADDRESS) return;
    setIsSubmitting(true);
    setLoadingMsg(`Resolving dispute as ${resolution}...`);
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'resolve_dispute',
        args: [campaignId, resolution]
      }));
      setLoadingMsg('Finalizing dispute resolution on-chain...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg(`Dispute resolved as ${resolution}.`);
    } catch (error: any) {
      console.error(error);
      alert('Dispute resolution failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const disputeVerdict = async () => {
    if (!client || !CONTRACT_ADDRESS) return;
    setIsSubmitting(true);
    setLoadingMsg('Disputing AI verdict...');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'dispute_verdict',
        args: [campaignId]
      }));
      setLoadingMsg('Freezing escrow funds and logging dispute...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Verdict disputed. Awaiting DAO/Admin review.');
    } catch (error: any) {
      console.error(error);
      alert('Dispute failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };


  // ---------------- CREATOR ACTIONS ----------------

  const submitVideoUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!client || !CONTRACT_ADDRESS) return;
    
    setIsSubmitting(true);
    setLoadingMsg('Awaiting AI Consensus... Scanning video for CTA, product mention, and checking blacklist.');
    setSuccessMsg('');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'submit_video',
        args: [campaignId, videoUrl]
      }));
      setLoadingMsg('Waiting for AI consensus consensus nodes to verify video...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Video submitted! The AI is processing the verdict.');
    } catch (error: any) {
      console.error(error);
      alert('Submission failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const approveCancel = async () => {
    if (!client || !CONTRACT_ADDRESS) return;
    setIsSubmitting(true);
    setLoadingMsg('Approving cancellation request...');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'approve_cancel',
        args: [campaignId]
      }));
      setLoadingMsg('Refunding brand escrow...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Cancellation approved. Funds refunded to Brand.');
    } catch (error: any) {
      console.error(error);
      alert('Approve failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const submitAppeal = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setLoadingMsg('Processing Appeal... AI Appellate Judge is reviewing your explanation.');
    setSuccessMsg('');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'appeal',
        args: [campaignId, appealText]
      }));
      setLoadingMsg('Waiting for AI Appellate judge to resolve conflict...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Appeal submitted and processed.');
    } catch (error: any) {
      console.error(error);
      alert('Appeal failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
      setAppealText('');
    }
  };

  const acceptCampaign = async () => {
    if (!client || !CONTRACT_ADDRESS || !campaignData) return;
    setIsSubmitting(true);
    setLoadingMsg('Accepting Campaign terms & depositing stake...');
    try {
      const escrowNum = BigInt(campaignData.escrow_amount);
      const stakeInWei = escrowNum / 5n; // 20% stake

      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'accept_campaign',
        args: [campaignId],
        value: stakeInWei
      }), 4, 1500, (attempt, err) => {
        const isRateLimit = err.message?.toLowerCase().includes('rate limit') || err.message?.toLowerCase().includes('rate-limit') || err.message?.toLowerCase().includes('too many requests') || err.message?.toLowerCase().includes('429');
        setLoadingMsg(isRateLimit 
          ? `Studionet Node rate-limited us. Pausing 3.5s & retrying (Attempt ${attempt}/4)...`
          : `Network busy. Retrying transaction (Attempt ${attempt}/4)...`
        );
      });
      setLoadingMsg('Confirming campaign acceptance and stake on-chain...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg(`Campaign accepted! Staked ${(Number(stakeInWei) / 1e18).toFixed(2)} GEN successfully.`);
    } catch (error: any) {
      console.error(error);
      alert('Accept failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const rejectCampaign = async () => {
    if (!client || !CONTRACT_ADDRESS) return;
    setIsSubmitting(true);
    setLoadingMsg('Rejecting Campaign...');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'reject_campaign',
        args: [campaignId]
      }));
      setLoadingMsg('Finalizing rejection on-chain...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Campaign rejected. Escrow refunded to the brand.');
    } catch (error: any) {
      console.error(error);
      alert('Reject failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  // ---------------- SHARED ACTIONS ----------------

  const finalizePayout = async () => {
    if (!client || !CONTRACT_ADDRESS) return;
    setIsSubmitting(true);
    setLoadingMsg('Finalizing payout...');
    try {
      const txHash = await callWithRetry(() => client.writeContract({
        address: CONTRACT_ADDRESS,
        account: { address: account as any },
        functionName: 'finalize_payout',
        args: [campaignId]
      }));
      setLoadingMsg('Finalizing release of escrow payout on-chain...');
      await client.waitForTransactionReceipt({ hash: txHash });
      fetchCampaign(campaignId);
      setSuccessMsg('Payout finalized successfully.');
    } catch (error: any) {
      console.error(error);
      alert('Finalize failed: ' + error.message);
    } finally {
      setIsSubmitting(false);
      setLoadingMsg('');
    }
  };

  const fetchCampaign = async (idToFetch: string = campaignId, retries: number = 4, isUserClick: boolean = false) => {
     if (!idToFetch || !client || !CONTRACT_ADDRESS) return;
     setSuccessMsg('');
     
     for (let attempt = 0; attempt < retries; attempt++) {
       try {
         const result = await callWithRetry(() => client.readContract({
           address: CONTRACT_ADDRESS,
           functionName: 'get_campaign',
           args: [idToFetch]
         }));
         if (result) {
           setCampaignData(JSON.parse(result as string));
           setCampaignId(idToFetch);
           fetchMyCampaigns();
           return;
         }
       } catch (err: any) {
         console.warn(`Fetch campaign attempt ${attempt + 1}/${retries} failed:`, err);
         if (attempt < retries - 1) {
           await new Promise((resolve) => setTimeout(resolve, 2000));
         }
       }
     }
     
     if (isUserClick) {
       alert("Campaign not found or contract error.");
     }
     setCampaignData(null);
     setCampaignId(idToFetch);
  };

  const fetchMyCampaigns = async () => {
    if (!account || !client || !CONTRACT_ADDRESS) return;
    try {
      const result = await callWithRetry(() => client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_my_campaigns',
        args: [account]
      }));
      if (result) {
        setMyCampaigns(JSON.parse(result as string));
      } else {
        setMyCampaigns([]);
      }
    } catch (err) {
      console.error("Failed to fetch my campaigns", err);
      setMyCampaigns([]);
    }
  };

  useEffect(() => {
    if (!account || !client) return;
    
    // Initial fetch on mount or account switch
    fetchMyCampaigns();
    if (campaignId) {
      fetchCampaign(campaignId, 1, false);
    }

    // Background polling every 6 seconds to keep Brand/Creator states in sync without F5
    const interval = setInterval(() => {
      fetchMyCampaigns();
      if (campaignId) {
        fetchCampaign(campaignId, 1, false);
      }
    }, 6000);

    return () => clearInterval(interval);
  }, [account, client, campaignId]);

  // Handle auto-connect on load and listen to account changes
  useEffect(() => {
    if (window.ethereum) {
      const handleAccounts = (accounts: string[]) => {
        if (accounts.length > 0) {
          const address = accounts[0];
          setAccount(address);
          const genClient = createClient({
            chain: studionet,
            account: address as `0x${string}`,
            provider: window.ethereum
          });
          setClient(genClient);
          localStorage.setItem('walletConnected', 'true');
        } else {
          setAccount(null);
          setClient(null);
          setCampaignData(null);
          localStorage.removeItem('walletConnected');
        }
      };

      if (localStorage.getItem('walletConnected') === 'true') {
        window.ethereum.request({ method: 'eth_accounts' })
          .then(handleAccounts)
          .catch((err: any) => console.error("Auto connect failed", err));
      }

      window.ethereum.on('accountsChanged', handleAccounts);
      return () => {
        window.ethereum.removeListener('accountsChanged', handleAccounts);
      };
    }
  }, []);

  const fillDemoData = () => {
    setNewCampId('summer_shoes_01');
    setCreatorAddress(account || '0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b');
    setEscrowAmount('5.0');
    setBlacklistKeywords('scam, fake product, fake discount');
    setProductName('girl sandals');
    setRequiredCta('add to cart');
    setRequiredLang('English, Japanese, Chinese');
    setCampaignDesc('Video review of children sandals, showcasing soft and comfortable design, with a shopping cart attached.');
    setBrandLogo("The word 'AffiliateGuard' next to a blue protective shield icon");
    setLogoUrl("https://affiliateguard.vercel.app/shield-logo.png");
  };

  // ---------------- MOCK DATA ----------------
  const MOCK_KOLS = [
    {
      id: 1,
      name: '@AlexTech',
      niche: 'Technology & Gadgets',
      followers: '1.2M',
      engagement: '8.5%',
      wallet: '0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
      avatar: '🧑‍💻',
      social: { twitter: 'twitter.com/alextech', tg: 't.me/alextech' }
    },
    {
      id: 2,
      name: '@SarahStyles',
      niche: 'Fashion & Beauty',
      followers: '850K',
      engagement: '12.1%',
      wallet: '0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b',
      avatar: '👩‍🎤',
      social: { twitter: 'twitter.com/sarahstyles', tg: 't.me/sarahstyles' }
    },
    {
      id: 3,
      name: '@FoodieDan',
      niche: 'Food & Lifestyle',
      followers: '2.4M',
      engagement: '6.2%',
      wallet: '0xa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0',
      avatar: '👨‍🍳',
      social: { twitter: 'twitter.com/foodiedan', tg: 't.me/foodiedan' }
    }
  ];

  const MOCK_BOUNTIES: any[] = [];

  const handleHireKOL = (wallet: string) => {
    setRole('BRAND');
    setCreatorAddress(wallet);
    setSuccessMsg('Creator selected! Please fill out the campaign details.');
    // Scroll to form
    const el = document.getElementById('dashboard-forms');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  const handleApplyBounty = (campaignId: string) => {
    setRole('CREATOR');
    setCampaignId(campaignId);
    setSuccessMsg('You are applying for a bounty! Please fetch the campaign and submit your video.');
    const el = document.getElementById('dashboard-forms');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
    fetchCampaign(campaignId);
  };

  return (
    <>
      <div className="app-container">
        <header className="app-header">
          <div className="logo-container">
            <a href="#" className="logo">AffiliateGuard</a>
            <nav className="nav-links">
              <a href="#">Dashboard</a>
              <a href="#">How it Works</a>
              <a href="#">Documentation</a>
            </nav>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            {account ? (
              <>
                <div className="account-pill">{account.slice(0,6)}...{account.slice(-4)}</div>
                <button className="btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} onClick={disconnectWallet}>Disconnect</button>
              </>
            ) : (
              <button className="btn-primary" onClick={connectWallet}>Connect Wallet</button>
            )}
          </div>
        </header>

        <main className="hero">
          <h1>Trustless Affiliate Escrow</h1>
          <p>A smart contract powered by GenLayer AI Consensus to verify, judge, and release cross-border video affiliate payouts automatically.</p>
        </main>
        
        <section className="features-section">
          <h4 className="section-title">How it works</h4>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">💰</div>
              <h4>1. Brand Escrows Funds</h4>
              <p>The brand deposits GEN tokens into the smart contract and sets the required tags, CTAs, and blacklist keywords.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🎥</div>
              <h4>2. Creator Submits Video</h4>
              <p>The KOL creates the video and submits the TikTok/Shorts URL directly. No Oracles needed.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h4>3. AI Consensus & Payout</h4>
              <p>GenLayer AI nodes analyze the content. If the consensus matches the brief, funds are instantly released.</p>
            </div>
          </div>
        </section>

        <div className="role-selector" id="dashboard-forms">
          <div className="role-toggle">
            <button 
              className={`role-btn ${role === 'EXPLORE' ? 'active' : ''}`}
              onClick={() => { setRole('EXPLORE'); setSuccessMsg(''); }}
            >
              Explore KOLs
            </button>
            <button 
              className={`role-btn ${role === 'BOUNTIES' ? 'active' : ''}`}
              onClick={() => { setRole('BOUNTIES'); setSuccessMsg(''); }}
            >
              Open Campaigns
            </button>
            <button 
              className={`role-btn ${role === 'BRAND' ? 'active' : ''}`}
              onClick={() => { setRole('BRAND'); setSuccessMsg(''); setIsCampaignCreated(false); setCreatedCampaignId(''); }}
            >
              Brand Dashboard
            </button>
            <button 
              className={`role-btn ${role === 'CREATOR' ? 'active' : ''}`}
              onClick={() => { setRole('CREATOR'); setSuccessMsg(''); }}
            >
              Creator Dashboard
            </button>
          </div>
        </div>

        {!CONTRACT_ADDRESS && (
           <div className="alert alert-error">
             <strong>Setup Required:</strong> Deploy the contract to GenLayer studionet and provide the address to begin.
           </div>
        )}

        {successMsg && (
          <div className="alert alert-success">
            <strong>Success:</strong> {successMsg}
          </div>
        )}

        {role === 'EXPLORE' && (
          <div className="marketplace">
            <h2 style={{ textAlign: 'center', borderBottom: 'none' }}>Creator Marketplace</h2>
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginBottom: '2rem' }}>Discover top verified creators and hire them directly via smart contracts.</p>
            <div className="kol-grid">
              {MOCK_KOLS.map(kol => (
                <div key={kol.id} className="kol-card">
                  <div className="kol-avatar">{kol.avatar}</div>
                  <h3 className="kol-name">{kol.name}</h3>
                  <p className="kol-niche">{kol.niche}</p>
                  
                  <div className="kol-stats">
                    <div className="stat-item">
                      <span className="stat-value">{kol.followers}</span>
                      <span className="stat-label">Followers</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-value">{kol.engagement}</span>
                      <span className="stat-label">Engagement</span>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', justifyContent: 'center' }}>
                    <a href={`https://${kol.social.twitter}`} target="_blank" rel="noreferrer" className="social-link">🐦 Twitter</a>
                    <a href={`https://${kol.social.tg}`} target="_blank" rel="noreferrer" className="social-link">✈️ Telegram</a>
                  </div>

                  <button className="btn-primary kol-hire-btn" onClick={() => handleHireKOL(kol.wallet)}>
                    Hire via Escrow
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {role === 'BOUNTIES' && (
          <div className="marketplace">
            <h2 style={{ textAlign: 'center', borderBottom: 'none' }}>Open Campaigns (Bounties)</h2>
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginBottom: '2rem' }}>Apply for open campaigns funded by verified brands.</p>
            {MOCK_BOUNTIES.length === 0 ? (
              <div className="alert alert-warning" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
                There are currently no open campaigns available. Brands must create a campaign first!
              </div>
            ) : (
              <div className="kol-grid">
                {MOCK_BOUNTIES.map(bounty => (
                  <div key={bounty.id} className="kol-card bounty-card">
                    <div className="verdict-header" style={{ marginBottom: '1rem' }}>
                      <span className="verdict-tag" style={{ background: 'var(--primary)', color: 'white' }}>{bounty.brand}</span>
                      <span className="confidence-score" style={{ color: 'var(--primary)', fontWeight: 'bold' }}>{bounty.reward}</span>
                    </div>
                    <h3 className="kol-name" style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>{bounty.id}</h3>
                    <p className="kol-niche" style={{ textAlign: 'left', marginBottom: '0.5rem' }}><strong>Reqs:</strong> {bounty.requirements}</p>
                    <p className="kol-niche" style={{ textAlign: 'left', color: 'var(--status-escalated)', fontSize: '0.85rem' }}><strong>Avoid:</strong> {bounty.blacklist}</p>
                    <button className="btn-primary kol-hire-btn" onClick={() => handleApplyBounty(bounty.id)}>
                      Apply & Submit Video
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {(role === 'BRAND' || role === 'CREATOR') && (
          <div className="dashboard">
            {/* Left Column: Input Forms */}
            {role === 'BRAND' ? (
              isCampaignCreated ? (
                <div className="panel" style={{ textAlign: 'center', padding: '3.5rem 2.25rem' }}>
                  <div style={{ fontSize: '4.5rem', marginBottom: '1.5rem', display: 'inline-block' }}>🎉</div>
                  <h2 style={{ borderBottom: 'none', marginBottom: '1rem', padding: 0, textAlign: 'center' }}>Campaign Created!</h2>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '2.5rem', fontSize: '1.05rem', lineHeight: '1.6' }}>
                    Campaign <strong style={{ color: 'var(--text-main)' }}>{createdCampaignId}</strong> has been successfully deployed on-chain and its escrow funds are locked securely in the smart contract.
                  </p>
                  <button 
                    className="btn-primary full-width" 
                    onClick={() => {
                      setIsCampaignCreated(false);
                      setCreatedCampaignId('');
                    }}
                  >
                    Create Another Campaign
                  </button>
                </div>
              ) : (
                <div className="panel">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
                    <h2 style={{ borderBottom: 'none', margin: 0, padding: 0 }}>Create New Campaign</h2>
                    <button type="button" className="btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }} onClick={fillDemoData}>Fill Demo</button>
                  </div>
                  <form onSubmit={createCampaign}>
                  <div className="form-group">
                    <label>Campaign ID</label>
                    <input type="text" placeholder="e.g., summer_shoes_01" value={newCampId} onChange={e => setNewCampId(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Creator Wallet Address</label>
                    <input type="text" placeholder="0x..." value={creatorAddress} onChange={e => setCreatorAddress(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Escrow Amount (GEN)</label>
                    <input type="number" step="0.01" placeholder="5.0" value={escrowAmount} onChange={e => setEscrowAmount(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Target Product Name</label>
                    <input type="text" placeholder="e.g., summer sandals" value={productName} onChange={e => setProductName(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Required Call-To-Action (CTA)</label>
                    <input type="text" placeholder="e.g., add to cart" value={requiredCta} onChange={e => setRequiredCta(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Required Localized Languages / Subtitles</label>
                    <input type="text" placeholder="e.g., English, Japanese, Chinese" value={requiredLang} onChange={e => setRequiredLang(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Campaign Description / Brief</label>
                    <textarea placeholder="Describe what the creator should do..." value={campaignDesc} onChange={e => setCampaignDesc(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Brand Logo Descriptor (Visual Description)</label>
                    <input type="text" placeholder="e.g., Silver bitten apple logo, or Nike swoosh text" value={brandLogo} onChange={e => setBrandLogo(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Logo Image Reference URL (Optional)</label>
                    <input type="text" placeholder="https://example.com/logo.png (or enter None)" value={logoUrl} onChange={e => setLogoUrl(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <div className="form-group">
                    <label>Blacklist Keywords (comma separated)</label>
                    <textarea placeholder="e.g., scam, fake product, fake discount" value={blacklistKeywords} onChange={e => setBlacklistKeywords(e.target.value)} required disabled={isSubmitting} />
                  </div>
                  <button type="submit" className="btn-primary full-width" disabled={isSubmitting || !account}>
                    Deposit Funds & Create
                  </button>
                </form>
                
                {isSubmitting && role === 'BRAND' && (
                  <div className="loader-container" style={{ marginTop: '1rem' }}>
                    <div className="spinner"></div>
                    <p className="loader-text">{loadingMsg}</p>
                  </div>
                )}
              </div>
            )) : (
              <div className="panel">
                <h2>Creator Actions</h2>
                {!campaignData ? (
                  <div className="alert alert-warning">Load a campaign to submit video.</div>
                ) : (
                  <>
                    {campaignData.status === 'PENDING_ACCEPTANCE' && (
                      <div className="alert alert-warning">
                        <div>
                          <strong style={{ fontSize: '1rem', display: 'block', marginBottom: '0.35rem' }}>🎉 New Campaign Offer!</strong>
                          <span>The Brand has deposited escrow funds. Please review campaign details and blacklist keywords carefully before accepting.</span>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                          <button type="button" className="btn-primary" style={{ flex: 1 }} onClick={acceptCampaign} disabled={isSubmitting}>
                            Accept Campaign
                          </button>
                          <button type="button" className="btn-danger" style={{ flex: 1 }} onClick={rejectCampaign} disabled={isSubmitting}>
                            Reject
                          </button>
                        </div>
                      </div>
                    )}
                    
                    {(campaignData.status === 'OPEN' || campaignData.status === 'CANCEL_REQUESTED' || campaignData.status === 'NEEDS_REVISION') && (
                      <>
                        {campaignData.status === 'CANCEL_REQUESTED' && (
                          <div className="alert alert-warning">
                            <div>
                              <strong style={{ fontSize: '1rem', display: 'block', marginBottom: '0.35rem' }}>⚠️ Cancellation Requested!</strong>
                              <span>The brand wants to cancel this campaign. If you haven't started, you can approve the cancellation to refund them. If you have already made the video, submit the URL below.</span>
                            </div>
                            <button type="button" className="btn-secondary full-width" style={{ marginTop: '0.5rem' }} onClick={approveCancel} disabled={isSubmitting}>
                              Approve Cancel & Refund
                            </button>
                          </div>
                        )}
                        {campaignData.status === 'NEEDS_REVISION' && (
                          <div className="alert alert-warning">
                            <strong style={{ fontSize: '1rem', display: 'block', marginBottom: '0.35rem' }}>🔄 Needs Revision!</strong>
                            <span>The AI rejected your video (Reason: {campaignData.reason}). You have 1 chance left to fix the video and resubmit!</span>
                          </div>
                        )}
                        <div className="alert" style={{ background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.25)', marginBottom: '1.25rem' }}>
                          <strong style={{ fontSize: '0.9rem', color: '#60a5fa', display: 'block', marginBottom: '0.35rem' }}>
                            🛡️ Evidence & Ownership Binding Requirement:
                          </strong>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5', display: 'block' }}>
                            Your video description or closed captions MUST include the verification tags below to bind the submission to your campaign and prevent replay attacks:
                          </span>
                          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem 0.75rem', borderRadius: '4px', marginTop: '0.5rem', fontFamily: 'monospace', fontSize: '0.8rem', color: '#93c5fd' }}>
                            [Campaign: {campaignId}] [Creator: {account ? account.slice(0, 10) + '...' : 'YourWallet'}]
                          </div>
                        </div>

                        <form onSubmit={submitVideoUrl}>
                          <div className="form-group">
                            <label>Video / Authenticated Media URL (TikTok/Reels/Shorts)</label>
                            <input 
                              type="url" 
                              placeholder="https://..." 
                              value={videoUrl}
                              onChange={e => setVideoUrl(e.target.value)}
                              required
                              disabled={isSubmitting}
                            />
                          </div>
                          <button type="submit" className="btn-primary full-width" disabled={isSubmitting || !account}>
                            Submit for AI Consensus
                          </button>
                        </form>
                      </>
                    )}

                    {campaignData.status === 'ESCALATED' && (
                      <div className="appeal-section" style={{ borderTop: 'none', paddingTop: 0, marginTop: 0 }}>
                        <h3>Submit Appeal</h3>
                        <p style={{fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem'}}>AI requires clarification. Please explain your creative context.</p>
                        
                        {campaignData.verdict !== 'NONE' && (
                          <div className="verdict-box verdict-escalate" style={{ marginBottom: '1.25rem', padding: '0.85rem', borderRadius: '6px', border: '1px solid var(--status-escalated)' }}>
                            <strong style={{ fontSize: '0.85rem', color: 'var(--status-escalated)', display: 'block', marginBottom: '0.35rem' }}>
                              ⚠️ Initial AI consensus issue: {campaignData.verdict} ({campaignData.confidence}% Confidence)
                            </strong>
                            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text)' }}>{campaignData.reason}</p>
                          </div>
                        )}

                        <form onSubmit={submitAppeal}>
                          <div className="form-group">
                            <textarea 
                              placeholder="Explain why the AI judge made a mistake..." 
                              value={appealText}
                              onChange={e => setAppealText(e.target.value)}
                              required
                              disabled={isSubmitting}
                            />
                          </div>
                          <button type="submit" className="btn-primary full-width" disabled={isSubmitting || !account}>
                            Submit to AI Appellate
                          </button>
                        </form>
                      </div>
                    )}

                    {(campaignData.status === 'CLOSED' || campaignData.status === 'CANCELLED') && (
                      <div className="alert alert-warning">This campaign is finished. No further actions can be taken.</div>
                    )}

                    {isSubmitting && (
                       <div className="loader-container">
                         <div className="spinner"></div>
                         <p className="loader-text">{loadingMsg}</p>
                       </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Right Column: Shared Campaign Details & My Campaigns (Separated Panels) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Panel 1: Campaign Details */}
              <div className="panel">
                <h2>Campaign Details</h2>
              <div className="form-group" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <input 
                  style={{ flex: '1 1 200px' }}
                  type="text" 
                  value={campaignId} 
                  onChange={e => setCampaignId(e.target.value)} 
                  placeholder="Enter Campaign ID to view"
                />
                <button className="btn-secondary" onClick={() => fetchCampaign(campaignId, 2, true)}>Load</button>
              </div>
              
              {campaignData && (
                <div className="campaign-data mt-4">
                   <div className="status-header" style={{ marginTop: '1.5rem' }}>
                     <h3>Current Status</h3>
                     <span className={`badge badge-${campaignData.status.toLowerCase()}`}>{campaignData.status}</span>
                   </div>
                   
                   <div className="data-list">
                     <div className="data-item">
                       <span className="data-label">Escrow Amount</span>
                       <span className="data-value">{Number(campaignData.escrow_amount) / 1e18} GEN</span>
                     </div>
                     {campaignData.creator_stake && Number(campaignData.creator_stake) > 0 && (
                        <div className="data-item">
                          <span className="data-label">Creator Stake</span>
                          <span className="data-value" style={{ color: '#ec4899', fontWeight: 'bold' }}>{Number(campaignData.creator_stake) / 1e18} GEN (Staked)</span>
                        </div>
                      )}
                     <div className="data-item">
                       <span className="data-label">Creator Address</span>
                       <span className="data-value mono">{campaignData.creator}</span>
                     </div>
                     {campaignData.campaign_desc && (
                       <div className="data-item">
                         <span className="data-label">Campaign Brief</span>
                         <span className="data-value" style={{ fontStyle: 'italic', fontWeight: 500 }}>{campaignData.campaign_desc}</span>
                       </div>
                     )}
                     {campaignData.product_name && (
                       <div className="data-item">
                         <span className="data-label">Target Product</span>
                         <span className="data-value">{campaignData.product_name}</span>
                       </div>
                     )}
                     {campaignData.required_cta && (
                       <div className="data-item">
                         <span className="data-label">Required CTA</span>
                         <span className="data-value">{campaignData.required_cta}</span>
                       </div>
                     )}
                     {campaignData.required_lang && (
                       <div className="data-item">
                         <span className="data-label">Required Languages / Subtitles</span>
                         <span className="data-value">{campaignData.required_lang}</span>
                       </div>
                     )}
                     {campaignData.brand_logo && campaignData.brand_logo !== 'None' && (
                       <div className="data-item">
                         <span className="data-label">Required Brand Logo</span>
                         <span className="data-value">{campaignData.brand_logo}</span>
                       </div>
                     )}
                     {campaignData.logo_url && campaignData.logo_url !== 'None' && (
                       <div className="data-item">
                         <span className="data-label">Logo Reference Image</span>
                         <span className="data-value mono" style={{ fontSize: '0.85rem' }}>
                           <a href={campaignData.logo_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'underline' }}>
                             {campaignData.logo_url}
                           </a>
                         </span>
                       </div>
                     )}
                     <div className="data-item">
                       <span className="data-label">Blacklist Keywords</span>
                       <span className="data-value">{campaignData.blacklist_keywords}</span>
                     </div>
                   </div>

                   {campaignData.verdict !== 'NONE' && (
                     <div className={`verdict-box verdict-${campaignData.verdict.toLowerCase().replace('appeal_', '')}`}>
                        <div className="verdict-header">
                          <span className="verdict-tag">{campaignData.verdict}</span>
                          <span className="confidence-score">{campaignData.confidence}% Confidence</span>
                        </div>
                        <p className="reason-text">{campaignData.reason}</p>
                     </div>
                   )}

                   {role === 'BRAND' && account && campaignData.brand && account.toLowerCase() !== campaignData.brand.toLowerCase() && (
                     <div className="alert alert-warning" style={{ marginTop: '1.5rem' }}>
                       <strong style={{ fontSize: '1.0rem', display: 'block', marginBottom: '0.35rem' }}>👀 Guest Mode</strong>
                       <span>You are not the brand owner of this campaign (Brand: <span className="mono" style={{ wordBreak: 'break-all' }}>{campaignData.brand}</span>). Cancel and Dispute actions are disabled.</span>
                     </div>
                   )}

                   {role === 'BRAND' && campaignData.status === 'OPEN' && account && campaignData.brand && account.toLowerCase() === campaignData.brand.toLowerCase() && (
                     <button onClick={requestCancelCampaign} disabled={isSubmitting} className="btn-secondary full-width" style={{ marginTop: '1.5rem', color: 'var(--status-escalated)' }}>
                       Request Cancel & Refund Escrow
                     </button>
                   )}

                   {role === 'BRAND' && campaignData.status === 'CANCEL_REQUESTED' && account && campaignData.brand && account.toLowerCase() === campaignData.brand.toLowerCase() && (
                     <div className="alert alert-warning" style={{ marginTop: '1.5rem' }}>
                       <p>Cancellation requested. Waiting for Creator to approve.</p>
                       <button onClick={forceCancelCampaign} disabled={isSubmitting} className="btn-secondary full-width" style={{ marginTop: '0.5rem', color: 'var(--status-escalated)' }}>
                         Force Cancel (If 7 days passed)
                       </button>
                     </div>
                   )}

                   {campaignData.status === 'AWAITING_PAYOUT' && (
                     <div className="alert alert-warning" style={{ marginTop: '1.5rem' }}>
                       <p><strong>Awaiting Payout</strong>: AI judged {campaignData.verdict}. Escrow is locked for 24 hours.</p>
                       <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                         <button onClick={finalizePayout} disabled={isSubmitting} className="btn-primary" style={{ flex: 1 }}>
                           Finalize Payout
                         </button>
                         {role === 'BRAND' && account && campaignData.brand && account.toLowerCase() === campaignData.brand.toLowerCase() && (
                           <button onClick={disputeVerdict} disabled={isSubmitting} className="btn-secondary" style={{ flex: 1, color: 'var(--status-escalated)' }}>
                             Dispute Verdict
                           </button>
                         )}
                       </div>
                     </div>
                   )}

                    {campaignData.status === 'DISPUTED' && (
                      <div className="alert alert-warning" style={{ marginTop: '1.5rem' }}>
                        <strong style={{ display: 'block', marginBottom: '0.5rem' }}>⚖️ Disputed Escrow</strong>
                        <p>The Brand has disputed the AI verdict. The authorized arbitrator or brand can resolve the dispute:</p>
                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                          <button onClick={() => resolveDispute('RELEASE')} disabled={isSubmitting} className="btn-primary" style={{ flex: 1, fontSize: '0.8rem' }}>
                            Award Creator
                          </button>
                          <button onClick={() => resolveDispute('SPLIT')} disabled={isSubmitting} className="btn-secondary" style={{ flex: 1, fontSize: '0.8rem' }}>
                            Split 50/50
                          </button>
                          <button onClick={() => resolveDispute('REFUND')} disabled={isSubmitting} className="btn-secondary" style={{ flex: 1, fontSize: '0.8rem', color: 'var(--status-escalated)' }}>
                            Refund Brand
                          </button>
                        </div>
                      </div>
                    )}
                </div>
              )}
            </div>
              {/* Panel 2: My Campaigns */}
              {account && (
                <div className="panel">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ borderBottom: 'none', margin: 0, padding: 0 }}>My Campaigns</h2>
                    <button className="btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }} onClick={fetchMyCampaigns}>Refresh</button>
                  </div>
                  {myCampaigns.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '1rem' }}>No campaigns found for this wallet.</p>
                  ) : (
                    <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {myCampaigns.map((camp: any) => (
                        <li key={camp.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                          <div>
                            <strong>{camp.id}</strong>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Status: {camp.status}</div>
                          </div>
                          <button className="btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} onClick={() => fetchCampaign(camp.id, 2, true)}>View</button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      <footer className="app-footer">
        <div className="footer-grid">
          <div className="footer-col">
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              🛡️ AffiliateGuard
            </h4>
            <p>Solving cross-border marketing disputes with trustless AI consensus and automatic crypto payouts.</p>
          </div>
          <div className="footer-col">
            <h4>Resources</h4>
            <ul>
              <li><a href="#">Documentation</a></li>
              <li><a href="#">GenLayer Network</a></li>
              <li><a href="#">GitHub Repo</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Legal</h4>
            <ul>
              <li><a href="#">Terms of Service</a></li>
              <li><a href="#">Privacy Policy</a></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2026 AffiliateGuard. Built on GenLayer Intelligent Contracts.</p>
        </div>
      </footer>
    </>
  );
}

export default App;
