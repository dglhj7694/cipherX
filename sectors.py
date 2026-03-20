# ══════════════════════════════════════════════════════════════
#  sectors.py — 섹터별 티커 그룹 관리 (2026 Q2 업데이트)
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
    # 📀 골든돔 (Golden Dome)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '📀빅테크/플랫폼': [
        'MSFT','AMZN','GOOGL','META','AAPL','IBM','DELL','HPE',
        'RBLX','RDDT','RUM',
    ],
    '📀반도체장비/제조(골든돔)': [
        'NVDA','AVGO','TSM','ASML','AMD','KLAC','AMAT','LRCX','QCOM','ARM',
        'MU','INTC','LSCC','AMKR','KLIC','TER','UCTT',
    ],
    '📀에너지/전력망(골든돔)': [
        'GEV','CEG','VST','ETN','PWR','HUBB','ITRI','POWL','FIX','STRL',
        'GNRC','WMS','PNR','VLTO',
    ],
    '📀방산/보안표준': [
        'LMT','RTX','NOC','LHX','HON','CRWD','PANW','FTNT','OKTA','CACI','PSN',
    ],

    '📀전력/산업인프라': [
        'VRT','ETN','GEV','PWR','NVT','EMR','HON','HUBB','GNRC','WMS',
        'PNR','VLTO','MOD','AY','CW','TDY','PSN','MRCY','TKR','KEYS',
        'CGNX','TRMB','PTC','ITRI','POWL','FIX','STRL',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🚀 제네시스 (Genesis)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '🚀클라우드/데이터(제네시스)': [
        'SNOW','MDB','NET','TEAM','ZS','S','DDOG','VRNS','PLTR',
        'FSLY','APPN','ZETA','DOCN','TENB',
    ],
    '🚀반도체소재/부품(제네시스)': [
        'ON','MPWR','MRVL','MCHP','WOLF','ACLS','ONTO','CAMT','FORM',
        'PLAB','CRDO','ALAB','VECO','COHU',
    ],
    '🚀핀테크/크립토': [
        'COIN','SQ','SOFI','HOOD','AFRM','LMND','UPST','MQ','GLBE',
        'JMIA','WRBY','DLO','RBLX','RDDT','RUM',
        'MARA','IREN','CLSK','WULF','BTMW',
    ],
    '🚀디지털헬스/바이오(제네시스)': [
        'VCYT','NTRA','TGTX','DNLI','HLNX','ABCL','PACB','EDIT',
        'EXAS','HIMS','SOPH',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔍 X10 세부 섹터
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '🔟냉각/열관리': [
        'MOD','FIX','NVT','SMCI','RFIL','AA','CARR','JCI','VRT',
    ],
    '🔟전력/인프라': [
        'MYRG','EME','PWR','PLPC','IESC','MTZ','DUK','TLN','SEI',
        'APLD','IREN','WULF','HUT','AEIS','AMSC','BE','ETN','GEV','NEE',
        'HUBB','ITRI','POWL','STRL','GNRC','WMS','PNR','VLTO',
    ],
    '🔟반도체장비/소재': [
        'PLAB','AEHR','SKYT','ASYS','CAMT','NVMI','KLIC','AMKR','ENTG',
        'FORM','ACMR','ATOM','GFS','WOLF','ASML','LRCX','KLAC',
        'ACLS','ONTO','VECO','COHU','TER','UCTT',
    ],
    '🔟칩설계/가속기': [
        'NVDA','AVGO','MRVL','AMD','ARM','MPWR','QCOM','INTC',
        'LSCC','ON','MU','MCHP',
    ],
    '🔟네트워킹/광통신': [
        'CRDO','FN','COHR','LITE','CIEN','MTSI','MKSI','ALAB','CLS',
        'AKAM','HLIT','INSG','ANET','CSCO','TSM','ASX','GLW',
        'LASR','POET','AAOI','TSEM','LWLG','INFN','VIAV','DY','APH',
    ],
    '🔟원자력/SMR': [
        'SMR','OKLO','LEU','BWXT','CCJ','VST','CEG','FLR','UEC','NNE',
        'NXE','UUUU','DNN','UROY','URG','EU','LTBR','ISO',
    ],
    '🔟로보틱스/물리AI': [
        'SYM','SERV','TER','KTOS','ISRG','ROK','AXON','PATH','TSLA',
        'EVLV','LIDR','HSAI','AUR','LAZR','INVZ','SOUN','AI','BBAI',
        'INOD','RRX','TDY','AMBA','AMAT','KEYS','TEL','TKR','ST','PTC',
        'MEI','PH','ZBRA','ALNT','ADI','CW','CGNX','ON',
        'RKT','APH','VICR','STRC','NOVT','ABB','FANUY','SYK','MBLY','EMR',
        'ACHR','JOBY','AVAV','RR',
    ],
    '🔟사이버보안': [
        'S','QLYS','CYBR','VRNS','FTNT','RBRK','BB','PANW','CRWD','ZS','NET',
        'OKTA','TENB','CACI',
    ],
    '🔟스토리지/메모리': [
        'WDC','MU','STX','PSTG','PENG','NTAP','DELL','SNDK',
    ],
    '🔟AI플랫폼/SW': [
        'INOD','FIVN','TDC','BOX','CRWV','NBIS','PLTR','SNOW','MDB',
        'SOUN','RSKD','PUBM','FTNT','MANH','CHKP','TEAM','DUOL','CVLT',
        'DDOG','TYL','PANW','NOW','MSFT','HUBS','META','ZS','GWRE',
        'RBRK','ORCL','UPST','ZETA','U','TEM','PGY','APP','FROG',
        'KVYO','OKTA','NET','AI','CRM','ADBE',
        'FSLY','APPN','DOCN',
    ],
    '🔟차세대에너지': [
        'OKLO','SMR','NNE','LEU','BWXT','LTBR','APLD','BE',
        'FLNC','STEM','NRGV','GWH','ENS','ENPH','SEDG','RUN','NPWR','SLRC','EOS',
    ],
    '🔟우주/항공/UAM': [
        'RKLB','ASTS','LUNR','PL','RDW','SPIR','BKSY','MNTS','GSAT',
        'IRDM','SATS','ACHR','JOBY','AVAV','KTOS','VSAT',
        'SIDU','LLAP',
    ],
    '🔟양자컴퓨팅': [
        'IONQ','RGTI','QBTS','QUBT','ARQQ','SKYT','RKTA',
    ],
    '🔟양자/차세대기술': [
        'IONQ','RGTI','QBTS','QUBT','RKTA','ACMR','AMBA',
        'SEVA','VICR','MG','HLIT','POWW',
    ],
    '🔟바이오/헬스': [
        'RXRX','SDGR','TMDX','EXAS','HIMS','VKTX','GRAL','GH','VCYT',
        'WGS','ABCL','PACB','EDIT','BEAM','NTLA','PRME','DNA','TXG',
        'TEM','TWST','DNLI','GDRX','AMWL',
        'NTRA','TGTX','HLNX','SOPH','UTHR',
    ],
    '🔟비트코인채굴': [
        'MARA','IREN','CLSK','WULF','BTMW',
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ⛏️ 원자재/자원
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '⛏️우라늄/핵연료': [
        'CCJ','UEC','NXE','UUUU','DNN','UROY','URG','EU','LEU','BWXT',
        'ISO',
    ],
    '⛏️리튬/배터리': [
        'ALB','SQM','LAC','SGML','IONR','NMG','NVX','WOLF',
        'ATLX','ELBM','DFLI','PLL','LICY','QS','SLDP','FREY',
    ],
    '⛏️구리/베이스메탈': [
        'FCX','SCCO','RIO','HBM','ERO','TGB',
        'IE','TMQ','KOS',
    ],
    '⛏️희토류/특수소재': [
        'MP','UAMY','TROX',
        'NB','IPX','PPTA','IDR','CRML','MTRN','COHR','PLPC','HXL',
    ],
}