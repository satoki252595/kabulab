import getStockFinancialInfo as gsfi
import screening as s
import createNotionDataFrame as cndf
import notionUp

#codeList = [code + '.T' for code in gsfi.getStockCodeDataFrame()['code'].tolist()]
codeList = ['9211.T','3393.T']
screened_stocks = s.screen_stocks(codeList)
notionUpDataFrame = cndf.createNotionUpDataFrame(screened_stocks)
notionUp.uploadToNotion(notionUpDataFrame)
