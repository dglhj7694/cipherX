# ══════════════════════════════════════════════════════════════
#  sectors.py — 섹터별 티커 그룹 관리
#  하나의 티커가 여러 섹터에 중복 포함 가능
# ══════════════════════════════════════════════════════════════

SECTOR_GROUPS = {

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ⭐ 핵심 워치리스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '⭐ TOP': [
        'PLAB','INOD','MYRG','LEU','MOD','SKYT','AEHR','ASYS','RFIL','CRDO',
        'FN','CAMT','NVMI','FIVN','SMR','NNE','SERV','MP','KLIC','APLD','PENG',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🚀 2026 로드맵
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '🚀 2026 로드맵': [
        'NVDA','AVGO','MRVL','AMD','ARM','MPWR','QCOM','TSM','ASML',
        'AMAT','LRCX','KLAC','VRT','ETN','GEV','PWR','NVT','ANET',
        'COHR','CIEN','FN','CEG','VST','CCJ','OKLO','SMR','NEE',
        'ISRG','SYM','SERV','PATH','PLTR','SNOW','MDB','TSLA',
        'CRWD','PANW','DDOG','NET','ZS','S','RXRX','SDGR','RKLB',
        'ASTS','MP','SNDK',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔍 X10 세부 섹터
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '냉각/열관리': [
        'MOD','FIX','NVT','SMCI','RFIL','AA','CARR','JCI','VRT',
    ],
    '전력/인프라': [
        'MYRG','EME','PWR','PLPC','IESC','MTZ','DUK','TLN','SEI',
        'APLD','IREN','WULF','HUT','AEIS','AMSC','BE','ETN','GEV','NEE',
    ],
    '반도체장비/소재': [
        'PLAB','AEHR','SKYT','ASYS','CAMT','NVMI','KLIC','AMKR','ENTG',
        'FORM','ACMR','ATOM','GFS','WOLF','ASML','LRCX','KLAC',
        'ACLS','ONTO','VECO','COHU','TER','UCTT',
    ],
    '칩설계/가속기': [
        'NVDA','AVGO','MRVL','AMD','ARM','MPWR','QCOM','INTC',
        'LSCC','ON','MU','MCHP',
    ],
    '네트워킹/광통신': [
        'CRDO','FN','COHR','LITE','CIEN','MTSI','MKSI','ALAB','CLS',
        'AKAM','HLIT','INSG','ANET','CSCO','TSM','ASX','GLW',
        'LASR','POET','AAOI','TSEM','LWLG','INFN','VIAV','DY','APH',
    ],
    '원자력/SMR': [
        'SMR','OKLO','LEU','BWXT','CCJ','VST','CEG','FLR','UEC','NNE',
        'NXE','UUUU','DNN','UROY','URG','EU',
    ],
    '로보틱스/물리AI': [
        'SYM','SERV','TER','KTOS','ISRG','ROK','AXON','PATH','TSLA',
        'EVLV','LIDR','HSAI','AUR','LAZR','INVZ','SOUN','AI','BBAI',
        'INOD','RRX','TDY','AMBA','AMAT','KEYS','TEL','TKR','ST','PTC',
        'MEI','PH','ZBRA','ALNT','ADI','CW','CGNX','ON',
        'RKT','APH','VICR','STRC','NOVT','ABB','FANUY','SYK','MBLY','EMR',
    ],
    '사이버보안': [
        'S','QLYS','CYBR','VRNS','FTNT','RBRK','BB','PANW','CRWD','ZS','NET',
        'OKTA','TENB',
    ],
    '스토리지/메모리': [
        'WDC','MU','STX','PSTG','PENG','NTAP','DELL','SNDK',
    ],
    'AI플랫폼/SW': [
        'INOD','FIVN','TDC','BOX','CRWV','NBIS','PLTR','SNOW','MDB',
        'SOUN','RSKD','PUBM','FTNT','MANH','CHKP','TEAM','DUOL','CVLT',
        'DDOG','TYL','PANW','NOW','MSFT','HUBS','META','ZS','GWRE',
        'RBRK','ORCL','UPST','ZETA','U','TEM','PGY','APP','FROG',
        'KVYO','OKTA','NET','AI','CRM','ADBE',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🏛️ 골든돔 & 제네시스
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '빅테크/플랫폼': [
        'MSFT','AMZN','GOOGL','META','AAPL','IBM','DELL','HPE','RBLX','RDDT','RUM',
    ],
    '전력/산업인프라': [
        'VRT','ETN','GEV','PWR','NVT','EMR','HON','HUBB','GNRC','WMS',
        'PNR','VLTO','MOD','AY','CW','TDY','PSN','MRCY','TKR','KEYS',
        'CGNX','TRMB','PTC',
    ],
    '핀테크/크립토': [
        'COIN','SQ','SOFI','HOOD','AFRM','LMND','UPST','MQ','GLBE',
        'JMIA','WRBY','DLO','MARA','IREN','CLSK','WULF',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🚀 텐배거 (문샷)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '🔋 차세대에너지': [
        'OKLO','SMR','NNE','LEU','BWXT','FLNC','STEM','NRGV','GWH',
        'ENS','ENPH','SEDG','RUN','NPWR','EOS',
    ],
    '우주/항공/UAM': [
        'RKLB','ASTS','LUNR','PL','RDW','SPIR','BKSY','MNTS','GSAT',
        'IRDM','SATS','ACHR','JOBY','AVAV','KTOS','VSAT',
    ],
    '양자컴퓨팅': [
        'IONQ','RGTI','QBTS','QUBT','ARQQ','SKYT',
    ],
    '바이오/헬스': [
        'RXRX','SDGR','TMDX','EXAS','HIMS','VKTX','GRAL','GH','VCYT',
        'WGS','ABCL','PACB','EDIT','BEAM','NTLA','PRME','DNA','TXG',
        'TEM','TWST','DNLI','GDRX','AMWL',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ⛏️ 원자재/자원
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '우라늄/핵연료': [
        'CCJ','UEC','NXE','UUUU','DNN','UROY','URG','EU','LEU','BWXT',
    ],
    '리튬/배터리': [
        'ALB','SQM','LAC','SGML','IONR','NMG','NVX','WOLF',
    ],
    '구리/베이스메탈': [
        'FCX','SCCO','RIO','HBM','ERO','TGB',
    ],
    '희토류/특수소재': [
        'MP','UAMY','TROX',
    ],
}